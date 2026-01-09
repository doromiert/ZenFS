######
# modules/zenfs.nix
######
{
  lib,
  pkgs,
  config,
  ...
}:

with lib;

let
  cfg = config.services.zenfs;

  # Python environment for the Gatekeeper script
  # Reduced dependencies as mounting.py uses standard library
  pyEnv = pkgs.python3;
in
{
  options.services.zenfs = {
    enable = mkEnableOption "ZenFS Core Architecture";

    mainDrive = mkOption {
      type = types.str;
      description = "UUID of the main system drive.";
    };

    bootDrive = mkOption {
      type = types.str;
      description = "UUID of the boot partition.";
    };

    swapSize = mkOption {
      type = types.int;
      default = 8192;
      description = "Size of the swapfile in MB.";
    };
  };

  config = mkIf cfg.enable {

    # [ ENV ] Core Variables
    environment.variables = {
      ZENFS_ROOT = "/System";
      ZENFS_GATE = "/System/ZenFS";
    };

    # [ SYSTEMD ] The Gatekeeper
    # Replaces the old activationScripts bash logic
    systemd.services.zenfs-gatekeeper = {
      description = "ZenFS Gatekeeper (Mounts & XDG Enforcer)";
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${pyEnv}/bin/python3 ${../scripts/core/mounting.py}";
        RemainAfterExit = true;
      };
    };

    # [ FILESYSTEMS ] Core Binds (Static)
    fileSystems."/" = {
      device = "/dev/disk/by-uuid/${cfg.mainDrive}";
      fsType = "btrfs";
      neededForBoot = true;
    };

    fileSystems."/boot" = {
      device = "/dev/disk/by-uuid/${cfg.bootDrive}";
      fsType = "vfat";
      neededForBoot = true;
    };

    # Basic System Structure Creation (Spec 4.1)
    systemd.tmpfiles.rules = [
      "d /System 0755 root root -"
      "d /System/ZenFS 0755 root root -"
      "d /System/ZenFS/Database 0700 root root -"
      "d /Users 0755 root root -"
      "d /Live 0755 root root -"
    ];
  };
}
