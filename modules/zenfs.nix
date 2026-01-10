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

  # Python environment for Gatekeeper & Indexer
  # [ DEPENDENCY ] Watchdog is required for the Librarian
  pyEnv = pkgs.python3.withPackages (ps: [ ps.watchdog ]);

  # Minter Utility
  zenfsMinter = pkgs.writeScriptBin "zenfs-mint" ''
    #!${pkgs.python3}/bin/python3
    import sys
    sys.path.append("${../scripts}/user")
    import mint
    if __name__ == "__main__":
        mint.main()
  '';
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

    # [ EXPOSE ] Add Minter and MergerFS to system path
    # MergerFS is required for the new Indexer logic
    environment.systemPackages = [
      zenfsMinter
      pkgs.mergerfs
    ];

    # [ SYSTEMD ] The Gatekeeper (Startup Setup)
    systemd.services.zenfs-gatekeeper = {
      description = "ZenFS Gatekeeper (Mounts & XDG Enforcer)";
      wantedBy = [ "multi-user.target" ];
      # [ CRITICAL ] Must run after local filesystems are mounted to bind them
      after = [ "local-fs.target" ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${pyEnv}/bin/python3 ${../scripts/core/mounting.py}";
        RemainAfterExit = true;
      };
    };

    # [ SYSTEMD ] The Librarian (Indexer Daemon)
    systemd.services.zenfs-indexer = {
      description = "ZenFS Librarian (Merger Manager)";
      wantedBy = [ "multi-user.target" ];
      after = [ "zenfs-gatekeeper.service" ]; # Wait for gates to bind
      # [ FIX ] Add mergerfs and util-linux (mount/umount) to path
      path = [
        pkgs.mergerfs
        pkgs.util-linux
      ];
      serviceConfig = {
        Type = "simple";
        Restart = "on-failure";
        # [ FIX ] Unbuffered I/O for instant logging
        Environment = "PYTHONUNBUFFERED=1";
        ExecStart = "${pyEnv}/bin/python3 ${../scripts/core/indexer.py}";
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
      "d /System/LocalHome 0755 root root -" # Required for MergerFS anchor
    ];
  };
}
