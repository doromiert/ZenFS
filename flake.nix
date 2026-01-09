{
  description = "ZenOS Component Flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    swisstag.url = "github:doromiert/swisstag";
    swisstag.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    {
      self,
      swisstag,
      ...
    }:
    let
      system = "x86_64-linux";
    in
    {
      # [ OVERLAY ]
      # Maps the external swisstag input to pkgs.swisstag
      overlays.default = final: prev: {
        swisstag = swisstag.packages.${prev.system}.default;
      };

      # [ MODULES ]
      nixosModules = {

        # The Default Bundle: Imports all capabilities + Overlay
        default =
          { ... }:
          {
            imports = [
              ./modules/zenfs.nix
              ./modules/janitor.nix
              ./modules/roaming.nix
            ];
            # Automatically inject the overlay so pkgs.swisstag is available
            nixpkgs.overlays = [ self.overlays.default ];
          };

        # Individual Modules
        zenfs = ./modules/zenfs.nix;

        janitor =
          { ... }:
          {
            imports = [ ./modules/janitor.nix ];
            # Janitor depends on pkgs.swisstag
            nixpkgs.overlays = [ self.overlays.default ];
          };

        roaming = ./modules/roaming.nix;
      };

      # [ PACKAGES ]
      # Expose swisstag for direct building if needed (nix build .#swisstag)
      packages.${system}.swisstag = swisstag.packages.${system}.default;
    };
}
