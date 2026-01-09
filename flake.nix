######
# ~/Projects/ZenFS/flake.nix
######
{
  description = "ZenFS Core Architecture & Janitor Suite";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    {
      nixosModules.default =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        {
          imports = [
            ./modules/zenfs.nix
            ./modules/roaming.nix
            ./modules/janitor.nix
          ];
        };
    };
}
