{
  description = "Development shell for the Netgear Nighthawk M6 Home Assistant integration";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
      ];
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              just
              python314
              uv
            ];

            # uv's downloaded interpreters cannot run on NixOS.
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${pkgs.python314}/bin/python3.14";
          };
        }
      );
      formatter = forAllSystems (system: nixpkgs.legacyPackages.${system}.nixfmt);
    };
}
