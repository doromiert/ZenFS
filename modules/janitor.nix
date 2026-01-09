######
# modules/janitor.nix
######
{
  lib,
  pkgs,
  config,
  ...
}:

with lib;

let
  cfg = config.services.zenfs.janitor;

  # [ FIX ] Capture the entire scripts directory to preserve structure
  # This ensures 'dumb.py' can resolve '../core/notify.py'
  zenfsScripts = ../scripts;

  janitorConfig = pkgs.writeText "janitor_config.json" (
    builtins.toJSON {
      dumb = {
        grace_period = cfg.dumb.gracePeriod;
        watched_dirs = cfg.dumb.watchedDirs;
        rules = cfg.dumb.rules;
      };
      music = {
        music_dir = cfg.music.musicDir;
        unsorted_dir = cfg.music.unsortedDir;
        split_symbols = cfg.music.artistSplitSymbols;
      };
      ml = {
        enabled = cfg.ml.enable;
        interval = cfg.ml.interval;
        scan_dirs = cfg.ml.scanDirs;
        suggestions_db = "/System/ZenFS/Database/suggestions.json";
      };
    }
  );

  # Added mutagen for Music Janitor, libnotify not needed here as python lib, but binary is needed in path
  janitorEnv = pkgs.python3.withPackages (ps: [
    ps.watchdog
    ps.pyyaml
    ps.pillow
    ps.mutagen
    ps.psutil
  ]);
in
{
  options.services.zenfs.janitor = {

    dumb = {
      enable = mkEnableOption "Dumb Janitor";
      interval = mkOption {
        type = types.str;
        default = "5min";
      };
      gracePeriod = mkOption {
        type = types.int;
        default = 60;
      };
      watchedDirs = mkOption {
        type = types.listOf types.str;
        default = [ "/home/doromiert/Downloads" ];
      };
      rules = mkOption {
        type = types.attrsOf (types.listOf types.str);
        default = { };
      };
    };

    music = {
      enable = mkEnableOption "Music Janitor";
      interval = mkOption {
        type = types.str;
        default = "30min";
      };
      musicDir = mkOption {
        type = types.str;
        default = "/home/doromiert/Music";
      };
      unsortedDir = mkOption {
        type = types.str;
        default = "/home/doromiert/Music/.database";
      };
      artistSplitSymbols = mkOption {
        type = types.listOf types.str;
        default = [
          ";"
          ","
        ];
      };
    };

    ml = {
      enable = mkEnableOption "ML Janitor (The Oracle)";
      interval = mkOption {
        type = types.str;
        default = "1h";
      };
      scanDirs = mkOption {
        type = types.listOf types.str;
        default = [
          "$HOME/Pictures"
          "$HOME/Documents"
        ];
      };
    };
  };

  config = mkIf (cfg.dumb.enable || cfg.music.enable || cfg.ml.enable) {

    # [ DUMB JANITOR ]
    systemd.services.zenfs-janitor-dumb = mkIf cfg.dumb.enable {
      description = "ZenFS Dumb Janitor (Sorting Deck)";
      environment.JANITOR_CONFIG = "${janitorConfig}";
      path = [ pkgs.libnotify ];
      serviceConfig = {
        Type = "oneshot";
        # Use the directory reference
        ExecStart = "${janitorEnv}/bin/python3 ${zenfsScripts}/janitor/dumb.py";
      };
    };

    systemd.timers.zenfs-janitor-dumb = mkIf cfg.dumb.enable {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnBootSec = "10m";
        OnUnitActiveSec = cfg.dumb.interval;
      };
    };

    # [ MUSIC JANITOR ]
    systemd.services.zenfs-janitor-music = mkIf cfg.music.enable {
      description = "ZenFS Music Janitor (Symlink Forest)";
      environment.JANITOR_CONFIG = "${janitorConfig}";
      path = [
        pkgs.coreutils
        pkgs.libnotify
      ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${janitorEnv}/bin/python3 ${zenfsScripts}/janitor/music.py";
      };
    };

    systemd.timers.zenfs-janitor-music = mkIf cfg.music.enable {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnBootSec = "15m";
        OnUnitActiveSec = cfg.music.interval;
      };
    };

    # [ ML JANITOR ]
    systemd.services.zenfs-janitor-ml = mkIf cfg.ml.enable {
      description = "ZenFS Oracle (Content Analysis)";
      environment.JANITOR_CONFIG = "${janitorConfig}";
      path = [ pkgs.libnotify ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${janitorEnv}/bin/python3 ${zenfsScripts}/janitor/ml.py";
      };
    };

    systemd.timers.zenfs-janitor-ml = mkIf cfg.ml.enable {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnBootSec = "30m";
        OnUnitActiveSec = cfg.ml.interval;
      };
    };
  };
}
