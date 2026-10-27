{
  # Development shell: everything to run the device software (mock mode) and the
  # server on a laptop, and to build the report.
  #
  #   nix develop        # or: direnv allow (uses .envrc)
  #   python3 -m pollen_device --config device/config.example.yaml --mock   (from device/)
  #   cd report && latexmk
  #
  # The Pi itself does not use this. It installs apt packages (device/install.sh),
  # because picamera2 and the GPIO libraries only work there.
  description = "Pollen sampler development shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs:
        let
          python = pkgs.python3.withPackages (ps: with ps; [
            flask
            requests
            pyyaml
            pillow
            numpy
          ]);
          # TeX Live "medium" plus what the AAU template in report/setup/preamble.tex loads.
          # CI uses a full TeX Live, so if CI builds and this does not, add the missing package here.
          tex = pkgs.texliveMedium.withPackages (ps: with ps; [
            latexmk
            babel-danish
            background
            everypage
            biblatex
            ntheorem
            todonotes
            titlesec
            lastpage
            tocbibind
            framed
            caption
          ]);
        in
        {
          default = pkgs.mkShell {
            packages = [ python tex ];
          };
        });
    };
}
