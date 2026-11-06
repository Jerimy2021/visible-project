{
  description = "Visible — WhatsApp → historial financiero + perfil crediticio (Women in Tech 2026)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            awscli2        # >= 2.32 para `aws login` (SSO, credenciales temporales)
            aws-sam-cli
            python312
            uv
            ruff
            nodejs_22
            pnpm
            just
            jq
            git
            gitleaks
            pre-commit
			python3Packages.cfn-lint
          ];

          shellHook = ''
            export AWS_PROFILE=visible
            export AWS_REGION=us-east-1

            cat <<'BANNER'
            ┌─ Visible · devShell ─────────────────────────────────┐
            │ AWS_PROFILE=visible  AWS_REGION=us-east-1            │
            │                                                      │
            │ just login   just whoami   just build   just deploy  │
            │ just logs fn=<nombre>   just test   just lint        │
            │ just fmt     just clean                              │
            └──────────────────────────────────────────────────────┘
            BANNER
          '';
        };
      });
}
