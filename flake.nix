{
  description = "Development shell for programming language learning labs";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
        "x86_64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          python = pkgs.python3;
        in {
          default = pkgs.mkShell {
            packages = [
              python
              pkgs.gcc
              pkgs.gnumake
              pkgs.rustc
              pkgs.cargo
              pkgs.nodejs
              pkgs.zig
              pkgs.ghc
              pkgs.cabal-install
              pkgs.sbcl
              pkgs.gnucobol
            ];

            shellHook = ''
              echo "learning-programming-languages dev shell"
              echo "Try: cd languages/c/hashtable && make test"
              echo "Try: cd languages/rust && cargo test"
              echo "Try: python3 languages/ml/src/test_ml.py"
              echo "Try: python3 languages/web3/blockchain/test_chain.py"
              echo "Try: node topics/functional-programming-basics/result.test.mjs"
              echo "Try: cd languages/zig && zig build test"
              echo "Try: cd languages/haskell && cabal test"
              echo "Try: cd languages/lisp && sbcl --script test/test.lisp"
              echo "Try: cd languages/cobol && ./test.sh"
            '';
          };
        });
    };
}
