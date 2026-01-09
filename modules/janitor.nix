{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.zenfs.janitor;

  # [ LOGIC ] Dumb Mode Script
  janitorDumb = pkgs.writers.writePython3Bin "janitor-dumb" {
    libraries = [ ];
  } (builtins.readFile ../scripts/janitorDumb.py);

  # [ LOGIC ] ML Mode Script
  janitorML = pkgs.writers.writePython3Bin "janitor-ml" {
    libraries = [ ];
  } (builtins.readFile ../scripts/janitorML.py);

  # [ CONFIGS ]
  dumbConfigJson = builtins.toJSON {
    watched_dirs = cfg.dumb.watchedDirs;
    grace_period = cfg.dumb.gracePeriod;
    rules = cfg.dumb.rules;
  };

  # Config for Janitor Music (View Generator)
  musicViewConfigJson = builtins.toJSON {
    inherit (cfg.music) musicDir unsortedDir artistSplitSymbols;
  };

  # Config for Swisstag (Tagger)
  swisstagConfigJson = builtins.toJSON {
    defaults = {
      rename = false; # Protection Mode
      match_filename = true;
      lyrics = {
        fetch = true;
        mode = "embed";
        source = "auto";
      };
      cover = {
        size = "1920x1920";
        keep_resized = true;
      };
    };
    separators = {
      artist = lib.concatStringsSep "" cfg.music.artistSplitSymbols;
      genre = "; ";
    };
    api_keys = { };
  };

  swisstagConfigFile = pkgs.writeText "swisstag-config.json" swisstagConfigJson;

in
{
  options.services.zenfs.janitor = {

    # --- Dumb Janitor ---
    dumb = {
      enable = lib.mkEnableOption "Dumb Janitor";
      watchedDirs = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ "$HOME/Downloads" ];
      };
      gracePeriod = lib.mkOption {
        type = lib.types.int;
        default = 60;
      };
      interval = lib.mkOption {
        type = lib.types.str;
        default = "5min";
      };
      rules = lib.mkOption {
        type = lib.types.attrsOf (lib.types.listOf lib.types.str);
        default = { };
      };
    };

    # --- Music Janitor (Spec 6) ---
    music = {
      enable = lib.mkEnableOption "Music View Generator (Symlink Forest)";

      tagging = {
        enable = lib.mkEnableOption "Swisstag Backend (Metadata Automation)";
      };

      unsortedDir = lib.mkOption {
        type = lib.types.str;
        default = "$HOME/Music/.database";
      };
      musicDir = lib.mkOption {
        type = lib.types.str;
        default = "$HOME/Music";
      };
      artistSplitSymbols = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ";" ];
      };
      interval = lib.mkOption {
        type = lib.types.str;
        default = "30min";
      };
    };

    # --- ML Janitor ---
    ml = {
      enable = lib.mkEnableOption "ML Janitor";
      smallModel = lib.mkOption {
        type = lib.types.str;
        default = "mk-quant-tiny-v1";
      };
      largeModel = lib.mkOption {
        type = lib.types.str;
        default = "mk-llm-7b-reasoner";
      };
      imageModel = lib.mkOption {
        type = lib.types.str;
        default = "mk-vision-pro-v2";
      };
      downTime = lib.mkOption {
        type = lib.types.submodule {
          options = {
            maxLoadAvg = lib.mkOption {
              type = lib.types.float;
              default = 1.5;
            };
            checkInterval = lib.mkOption {
              type = lib.types.str;
              default = "30min";
            };
          };
        };
        default = { };
      };
    };
  };

  config = lib.mkMerge [

    # [ DUMB SERVICE ]
    (lib.mkIf cfg.dumb.enable {
      systemd.user.services.zenfs-janitor-dumb = {
        description = "ZenFS Janitor (Dumb Mode)";
        environment.JANITOR_CONFIG = dumbConfigJson;
        path = [ pkgs.lsof ];
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${janitorDumb}/bin/janitor-dumb";
        };
      };
      systemd.user.timers.zenfs-janitor-dumb = {
        partOf = [ "zenfs-janitor-dumb.service" ];
        wantedBy = [ "timers.target" ];
        timerConfig = {
          OnBootSec = "5min";
          OnUnitActiveSec = cfg.dumb.interval;
        };
      };
    })

    # [ MUSIC SERVICE: View Generator ]
    (lib.mkIf cfg.music.enable {
      systemd.user.services.zenfs-janitor-music = {
        description = "ZenFS Music View Generator (Symlink Forest)";
        environment.JANITOR_MUSIC_CONFIG = musicViewConfigJson;
        # Uses the overlay package janitorMusic
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${pkgs.janitorMusic}/bin/janitor-music";
        };
      };
      systemd.user.timers.zenfs-janitor-music = {
        partOf = [ "zenfs-janitor-music.service" ];
        wantedBy = [ "timers.target" ];
        timerConfig = {
          OnBootSec = "15min";
          OnUnitActiveSec = cfg.music.interval;
        };
      };
    })

    # [ MUSIC SERVICE: Tagger (Swisstag) ]
    (lib.mkIf cfg.music.tagging.enable {
      systemd.user.services.zenfs-swisstag = {
        description = "ZenFS Music Tagger (Swisstag)";
        environment.SWISSTAG_CONFIG = "${swisstagConfigFile}";
        serviceConfig = {
          Type = "oneshot";
          # Runs in Album mode on the database
          ExecStart = "${pkgs.swisstag}/bin/swisstag -d network,cmd --album \"${cfg.music.unsortedDir}\"";
        };
      };
      systemd.user.timers.zenfs-swisstag = {
        partOf = [ "zenfs-swisstag.service" ];
        wantedBy = [ "timers.target" ];
        timerConfig = {
          OnBootSec = "20min";
          OnUnitActiveSec = "1h";
        }; # Tagging runs less often
      };
    })

    # [ ML SERVICE ]
    (lib.mkIf cfg.ml.enable {
      systemd.user.services.zenfs-janitor-ml = {
        description = "ZenFS Janitor (ML Mode)";
        environment = {
          ZENFS_MODEL_SMALL = cfg.ml.smallModel;
          ZENFS_MODEL_LARGE = cfg.ml.largeModel;
          ZENFS_MODEL_IMAGE = cfg.ml.imageModel;
          ZENFS_LOAD_THRESHOLD = toString cfg.ml.downTime.maxLoadAvg;
        };
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${janitorML}/bin/janitor-ml";
        };
      };
      systemd.user.timers.zenfs-janitor-ml = {
        partOf = [ "zenfs-janitor-ml.service" ];
        wantedBy = [ "timers.target" ];
        timerConfig = {
          OnBootSec = "10min";
          OnUnitActiveSec = cfg.ml.downTime.checkInterval;
        };
      };
    })
  ];
}
