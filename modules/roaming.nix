######
# modules/roaming.nix
######
{
  lib,
  pkgs,
  config,
  ...
}:

with lib;

let
  cfg = config.services.zenfs.roaming;

  # [ FIX ] Capture scripts directory
  zenfsScripts = ../scripts;

  # Python environment with necessary disk tools
  roamingEnv = pkgs.python3.withPackages (ps: [ ps.psutil ]);
in
{
  options.services.zenfs.roaming = {
    enable = mkEnableOption "ZenFS Roaming Protocol";

    automount = mkOption {
      type = types.bool;
      default = true;
      description = "Automatically mount drives containing a .zenos.json identity file.";
    };

    mountPoint = mkOption {
      type = types.str;
      default = "/Mount/Roaming";
      description = "Base directory for mounting roaming drives.";
    };
  };

  config = mkIf cfg.enable {

    # [ SERVICE ] The Nomad (Reconciler)
    systemd.services.zenfs-roaming = {
      description = "ZenFS Roaming (The Nomad)";
      path = [
        pkgs.libnotify
        pkgs.util-linux
      ];
      serviceConfig = {
        Type = "oneshot";
        Environment = "ZENFS_ROAMING_ROOT=${cfg.mountPoint}";
        ExecStart = "${roamingEnv}/bin/python3 ${zenfsScripts}/core/roaming.py";
      };
    };

    # [ UDEV ] Trigger on Block Device Events
    services.udev.extraRules = ''
      SUBSYSTEM=="block", ACTION=="add|remove", ENV{ID_FS_USAGE}=="filesystem", RUN+="${pkgs.systemd}/bin/systemctl start zenfs-roaming.service"
    '';

    # Ensure mount points exist
    systemd.tmpfiles.rules = [
      "d ${cfg.mountPoint} 0755 root root -"
      "d /Live/Drives 0755 root root -"
    ];
  };
}
