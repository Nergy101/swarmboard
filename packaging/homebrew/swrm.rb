# Homebrew formula for swrm (the swarmboard CLI).
#
# Lives in the tap repo `homebrew-swrm`; install with:
#   brew tap Nergy101/swrm https://github.com/Nergy101/homebrew-swrm
#   brew install swrm
#
# NOTE (release discipline): for every release, update `version` and `sha256`
# with the checksum of the swarmboard sdist on the PyPI release page
# (https://pypi.org/project/swarmboard/#files). The placeholder below fails
# `brew install` on purpose until it is replaced, so a release can never ship
# silently unverified.
class Swrm < Formula
  desc "CLI-first kanban board for agent swarms"
  homepage "https://github.com/Nergy101/swarmboard"
  url "https://files.pythonhosted.org/packages/source/s/swarmboard/swarmboard-0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  # TODO: pick an actual license for the repo and mirror it here.
  license :unknown

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_includes shell_output("#{bin}/swrm --version"), "swrm"
  end
end
