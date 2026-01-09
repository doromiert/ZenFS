{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.zenfs;

  bindDir = category: source: {
    name = "/Config/${category}";
    value = {
      device = "/etc/${source}";
      options = [ "bind" ];
    };
  };

  linkFiles =
    category: files: map (file: "L+ /Config/${category}/${file} - - - - /etc/${file}") files;

  networkFiles = [
    "hosts"
    "resolv.conf"
    "resolvconf.conf"
    "hostname"
    "ethertypes"
    "host.conf"
    "ipsec.secrets"
    "netgroup"
    "protocols"
    "rpc"
    "services"
  ];

  securityFiles = [ "sudoers" ];

  systemFiles = [
    "fstab"
    "os-release"
    "profile"
    "locale.conf"
    "vconsole.conf"
    "machine-id"
    "localtime"
    "inputrc"
    "issue"
    "kbd"
    "login.defs"
    "lsb-release"
    "man_db.conf"
    "nanorc"
    "nscd.conf"
    "nsswitch.conf"
    "terminfo"
    "zoneinfo"
  ];

  userFiles = [
    "passwd"
    "group"
    "shadow"
    "shells"
    "subgid"
    "subuid"
    "bashrc"
    "bash_logout"
    "zshrc"
    "zshenv"
    "zprofile"
    "zinputrc"
  ];

in
{
  options.services.zenfs = {
    enable = lib.mkEnableOption "ZenFS Hierarchy (For ZenOS)";

    mainDrive = lib.mkOption {
      type = lib.types.str;
      description = "UUID of the main system drive.";
    };

    bootDrive = lib.mkOption {
      type = lib.types.str;
      description = "UUID of the boot partition.";
    };

    fsType = lib.mkOption {
      type = lib.types.str;
      default = "btrfs";
      description = "Filesystem type for the main drive.";
    };

    swapSize = lib.mkOption {
      type = lib.types.int;
      default = 8192;
      description = "Size of the swapfile in MB.";
    };
  };

  config = lib.mkIf cfg.enable {
    # [ IDENTITY ] ZenOS Documentation Override
    documentation.enable = false;
    documentation.nixos.enable = false;
    documentation.man.enable = false;

    # [ SPEC 1.0 ] ZENFS ROOT STRUCTURE

    # --- BIND MOUNTS (The ZenFS Layer) ---
    fileSystems =
      builtins.listToAttrs [
        (bindDir "Audio/Pipewire" "pipewire")
        (bindDir "Audio/Alsa" "alsa")
        (bindDir "Bluetooth" "bluetooth")
        (bindDir "Desktop/XDG" "xdg")
        (bindDir "Desktop/GDM" "gdm")
        (bindDir "Desktop/Plymouth" "plymouth")
        (bindDir "Desktop/Remote" "gnome-remote-desktop")
        (bindDir "Desktop/DConf" "dconf")
        (bindDir "Display/X11" "X11")
        (bindDir "Fonts" "fonts")
        (bindDir "Hardware/Udev" "udev")
        (bindDir "Hardware/LVM" "lvm")
        (bindDir "Hardware/Modprobe" "modprobe.d")
        (bindDir "Hardware/Modules" "modules-load.d")
        (bindDir "Hardware/BlockDev" "libblockdev")
        (bindDir "Hardware/UDisks" "udisks2")
        (bindDir "Hardware/UPower" "UPower")
        (bindDir "Hardware/Qemu" "qemu")
        (bindDir "Network/Manager" "NetworkManager")
        (bindDir "Nix" "nix")
        (bindDir "Zero/NixOS" "nixos")
        (bindDir "Zero/Scripts" "zenos")
        (bindDir "Services/Systemd" "systemd")
        (bindDir "Services/DBus" "dbus-1")
        (bindDir "Services/Avahi" "avahi")
        (bindDir "Services/Geoclue" "geoclue")
        (bindDir "Security/PAM" "pam.d")
        (bindDir "Security/SSH" "ssh")
        (bindDir "Security/SSL" "ssl")
        (bindDir "Security/Polkit" "polkit-1")
        (bindDir "Misc" "")
      ]

      // {
        "/" = {
          device = "/dev/disk/by-uuid/${cfg.mainDrive}";
          fsType = cfg.fsType;
          neededForBoot = true;
        };
        "/boot" = {
          device = "/dev/disk/by-uuid/${cfg.bootDrive}";
          fsType = "vfat";
          neededForBoot = true;
        };
        "/System/nix" = {
          device = "/nix";
          fsType = "none";
          options = [ "bind" ];
          neededForBoot = true;
        };

        "/System/Boot" = {
          device = "/boot";
          options = [ "bind" ];
        };
        "/System/Store" = {
          device = "/nix/store";
          options = [ "bind" ];
        };
        "/System/Current" = {
          device = "/run/current-system";
          options = [ "bind" ];
        };
        "/System/Booted" = {
          device = "/run/booted-system";
          options = [ "bind" ];
        };
        "/System/Binaries" = {
          device = "/run/current-system/sw/bin";
          options = [ "bind" ];
        };
        "/System/Modules" = {
          device = "/run/current-system/kernel-modules";
          options = [ "bind" ];
        };
        "/System/Firmware" = {
          device = "/run/current-system/firmware";
          options = [ "bind" ];
        };
        "/System/Graphics" = {
          device = "/run/opengl-driver";
          options = [ "bind" ];
        };
        "/System/Wrappers" = {
          device = "/run/wrappers";
          options = [ "bind" ];
        };

        "/System/State" = {
          device = "/var/lib";
          options = [ "bind" ];
        };
        "/System/History" = {
          device = "/nix/var/nix/profiles";
          options = [ "bind" ];
        };
        "/System/Logs" = {
          device = "/var/log";
          options = [ "bind" ];
        };

        "/Live/dev" = {
          device = "/dev";
          options = [ "bind" ];
        };
        "/Live/proc" = {
          device = "/proc";
          options = [ "bind" ];
        };
        "/Live/sys" = {
          device = "/sys";
          options = [ "bind" ];
        };
        "/Live/run" = {
          device = "/run";
          options = [ "bind" ];
        };
        "/Live/Temp" = {
          device = "/tmp";
          options = [ "bind" ];
        };
        "/Live/Memory" = {
          device = "/dev/shm";
          options = [ "bind" ];
        };

        "/Live/Services" = {
          device = "/run/systemd";
          options = [ "bind" ];
        };
        "/Live/Network" = {
          device = "/run/NetworkManager";
          options = [ "bind" ];
        };
        "/Live/Sessions" = {
          device = "/run/user";
          options = [ "bind" ];
        };

        "/Live/Input" = {
          device = "/dev/input";
          options = [ "bind" ];
        };
        "/Live/Video" = {
          device = "/dev/dri";
          options = [ "bind" ];
        };
        "/Live/Sound" = {
          device = "/dev/snd";
          options = [ "bind" ];
        };

        "/Live/Drives/ID" = {
          device = "/dev/disk/by-id";
          options = [ "bind" ];
        };
        "/Live/Drives/Label" = {
          device = "/dev/disk/by-label";
          options = [ "bind" ];
        };
        "/Live/Drives/Partitions" = {
          device = "/dev/disk/by-partlabel";
          options = [ "bind" ];
        };
        "/Live/Drives/Physical" = {
          device = "/dev/disk/by-path";
          options = [ "bind" ];
        };

        "/Mount/Drives" = {
          device = "/mnt";
          options = [ "bind" ];
        };
        "/Mount/Removable" = {
          device = "/run/media";
          options = [ "bind" ];
        };
      };

    swapDevices = [
      {
        device = "/Live/swapfile";
        size = cfg.swapSize;
      }
    ];

    # [ ACTION ] Activation Script for ZenFS User Gates
    # Automatically creates XDG dirs and binds users to /Users
    system.activationScripts.zenfsUsers = {
      text = ''
        echo "ZenFS: Binding users and initializing Gates..."
        mkdir -p /Users

        bind_user() {
            local src=$1
            local dest=$2
            
            # 1. Bind to /Users
            if [ ! -d "$dest" ]; then mkdir -p "$dest"; fi
            if ! mountpoint -q "$dest"; then mount --bind "$src" "$dest"; fi
            
            # 2. Identify User UID/GID for permission fixing
            # (Activation scripts run as root, so we must correct ownership)
            local user_owner
            user_owner=$(stat -c "%u:%g" "$src")

            # 3. [ CUSTOM ] Autogen XDG Directories
            # Projects, 3D, Android, AI, Apps & Scripts, Doom, Rift, Misc, Passwords
            local xdg_dirs=("Projects" "3D" "Android" "AI" "Apps & Scripts" "Doom" "Rift" "Misc" "Passwords")
            
            for dir in "''${xdg_dirs[@]}"; do
                local target="$src/$dir"
                if [ ! -d "$target" ]; then
                    mkdir -p "$target"
                    chown "$user_owner" "$target"
                fi
            done

            # 4. [ SPEC 6.1 ] Music Source of Truth
            if [ -d "$src/Music" ]; then
                mkdir -p "$src/Music/.database"
                chmod 700 "$src/Music/.database"
                chown "$user_owner" "$src/Music/.database"
            fi

            # 5. [ SPEC 2.2 ] The Cluster Protocol
            if [ -d "$src/Downloads" ]; then
                mkdir -p "$src/Downloads/Waiting"
                chown "$user_owner" "$src/Downloads/Waiting"
            fi
        }

        # Iterate all users in /home
        for user_dir in /home/*; do
          if [ -d "$user_dir" ]; then
            user_name=$(basename "$user_dir")
            bind_user "$user_dir" "/Users/$user_name"
          fi
        done

        # Bind Admin (Root) - Note: chown logic above might warn on root but works
        bind_user "/root" "/Users/Admin"
      '';
      deps = [ ];
    };

    systemd.services.zenfs-drive-daemon = {
      description = "ZenFS Dynamic Drive Linker";
      wantedBy = [ "multi-user.target" ];
      path = with pkgs; [
        util-linux
        coreutils
        systemd
        findutils
        gnugrep
      ];
      script = ''
        TARGET_DIR="/Live/Drives/Nodes"
        mkdir -p "$TARGET_DIR"
        sync_drives() {
            find "$TARGET_DIR" -type l -delete
            for dev in /dev/sd* /dev/nvme*; do
                [ -e "$dev" ] || continue
                ln -sf "$dev" "$TARGET_DIR/$(basename "$dev")"
            done
        }
        sync_drives
        udevadm monitor --subsystem-match=block --udev | while read -r line; do
            if echo "$line" | grep -qE "add|remove|change"; then
                sleep 0.2; sync_drives
            fi
        done
      '';
      serviceConfig = {
        Type = "simple";
        Restart = "always";
        RestartSec = "5s";
      };
    };

    systemd.tmpfiles.rules = [
      "f+ /.hidden 0644 root root - bin\\nboot\\ndev\\netc\\nhome\\nlib\\nlib64\\nmnt\\nnix\\nopt\\nproc\\nroot\\nrun\\nsrv\\nsys\\ntmp\\nusr\\nvar"
      "d /System 0755 root root -"
      "d /System/nix 0755 root root -"
      "d /System/ZenFS 0755 root root -"
      "d /System/ZenFS/Database 0700 root root -"
      "d /Config 0755 root root -"
      "d /Config/Misc 0755 root root -"
      "d /Config/Audio 0755 root root -"
      "d /Config/Audio/Pipewire 0755 root root -"
      "d /Config/Audio/Alsa 0755 root root -"
      "d /Config/Bluetooth 0755 root root -"
      "d /Config/Desktop 0755 root root -"
      "d /Config/Desktop/XDG 0755 root root -"
      "d /Config/Desktop/GDM 0755 root root -"
      "d /Config/Desktop/Plymouth 0755 root root -"
      "d /Config/Desktop/Remote 0755 root root -"
      "d /Config/Desktop/DConf 0755 root root -"
      "d /Config/Display 0755 root root -"
      "d /Config/Display/X11 0755 root root -"
      "d /Config/Fonts 0755 root root -"
      "d /Config/Hardware 0755 root root -"
      "d /Config/Hardware/Udev 0755 root root -"
      "d /Config/Hardware/LVM 0755 root root -"
      "d /Config/Hardware/Modprobe 0755 root root -"
      "d /Config/Hardware/Modules 0755 root root -"
      "d /Config/Hardware/BlockDev 0755 root root -"
      "d /Config/Hardware/UDisks 0755 root root -"
      "d /Config/Hardware/UPower 0755 root root -"
      "d /Config/Hardware/Qemu 0755 root root -"
      "d /Config/Network 0755 root root -"
      "d /Config/Network/Manager 0755 root root -"
      "d /Config/Nix 0755 root root -"
      "d /Config/Zero 0755 root root -"
      "d /Config/Zero/NixOS 0755 root root -"
      "d /Config/Zero/Scripts 0755 root root -"
      "d /Config/Services 0755 root root -"
      "d /Config/Services/Systemd 0755 root root -"
      "d /Config/Services/DBus 0755 root root -"
      "d /Config/Services/Avahi 0755 root root -"
      "d /Config/Services/Geoclue 0755 root root -"
      "d /Config/Security 0755 root root -"
      "d /Config/Security/PAM 0755 root root -"
      "d /Config/Security/SSH 0755 root root -"
      "d /Config/Security/SSL 0755 root root -"
      "d /Config/Security/Polkit 0755 root root -"
      "d /Config/System 0755 root root -"
      "d /Config/User 0755 root root -"
    ]
    ++ (linkFiles "Network" networkFiles)
    ++ (linkFiles "Security" securityFiles)
    ++ (linkFiles "System" systemFiles)
    ++ (linkFiles "User" userFiles)
    ++ [
      "d /Mount 0755 root root -"
      "L+ /Mount/Drives - - - - /mnt"
      "L+ /Mount/Removable - - - - /run/media"
      "d /Mount/Roaming 0755 root root -"
      "d /Apps 0755 root root -"
      "L+ /Apps/System - - - - /run/current-system/sw/bin"
      "d /Live 0755 root root -"
      "d /Live/Temp 1777 root root -"
      "d /Live/Memory 1777 root root -"
      "d /Live/Services 0755 root root -"
      "d /Live/Network 0755 root root -"
      "d /Live/Sessions 0755 root root -"
      "d /Live/Input 0755 root root -"
      "d /Live/Video 0755 root root -"
      "d /Live/Sound 0755 root root -"
      "d /Live/Drives 0755 root root -"
      "d /Live/Drives/Nodes 0755 root root -"
      "d /Live/Drives/ID 0755 root root -"
      "d /Live/Drives/Label 0755 root root -"
      "d /Live/Drives/Partitions 0755 root root -"
      "d /Live/Drives/Physical 0755 root root -"
      "d /Users 0755 root root -"
    ];

    environment.variables = {
      ZENFS_ROOT = "/System";
      ZENFS_CONFIG = "/Config";
      ZENFS_GATE = "/System/ZenFS";

      # [ CUSTOM ] Autogen XDG Variables
      XDG_PROJECTS_DIR = "$HOME/Projects";
      XDG_THREED_DIR = "$HOME/3D";
      XDG_ANDROID_DIR = "$HOME/Android";
      XDG_AI_DIR = "$HOME/AI";
      XDG_APPS_SCRIPTS_DIR = "$HOME/Apps & Scripts";
      XDG_DOOM_DIR = "$HOME/Doom";
      XDG_RIFT_DIR = "$HOME/Rift";
      XDG_MISC_DIR = "$HOME/Misc";
      XDG_PASSWORDS_DIR = "$HOME/Passwords";
    };
  };
}
