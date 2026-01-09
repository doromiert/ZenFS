{
  description = "ZenOS Component Flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";

      # [ LOGIC ] Custom Overlay for Swisstag & Dependencies
      swisstagOverlay = final: prev: {
        swisstag =
          let
            python = final.python3;

            # 3. Fetch Swisstag Source from GitHub
            swisstagSrc = final.fetchFromGitHub {
              owner = "doromiert";
              repo = "swisstag";
              # You can pin a specific commit hash here for stability if needed
              # rev = "...";
              # sha256 = "...";
              rev = "main"; # Fetching HEAD of main for now
              hash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="; # Update this hash once known
            };

          in
          final.pkgs.stdenv.mkDerivation {
            name = "swisstag";
            src = swisstagSrc;

            nativeBuildInputs = [ final.makeWrapper ];

            # Environment with all deps
            propagatedBuildInputs = [
              (python.withPackages (
                ps: with ps; [
                  mutagen
                  musicbrainzngs
                  thefuzz
                  requests
                  unidecode
                  pillow
                  beautifulsoup4
                  rapidfuzz
                ]
              ))
              final.chromaprint
            ];

            installPhase = ''
              mkdir -p $out/bin
              # Assuming the script is named swisstag.py in the root of the repo
              cp swisstag.py $out/bin/swisstag
              chmod +x $out/bin/swisstag
            '';

            postFixup = ''
              wrapProgram $out/bin/swisstag \
                --prefix PATH : ${final.lib.makeBinPath [ final.chromaprint ]}
            '';
          };
      };

      pkgs = import nixpkgs {
        inherit system;
        overlays = [ swisstagOverlay ];
        config.allowUnfree = true;
      };

    in
    {
      nixosModules = {
        default = {
          imports = [
            ./modules/zenfs.nix
            ./modules/janitor.nix
          ];
        };
        zenfs = ./modules/zenfs.nix;
        janitor = ./modules/janitor.nix;
      };

      # Export packages for debugging
      packages.${system}.swisstag = pkgs.swisstag;
    };
}
