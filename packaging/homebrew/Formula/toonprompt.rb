class Toonprompt < Formula
  include Language::Python::Virtualenv

  desc "Universal prompt optimization wrapper for AI coding CLIs"
  homepage "https://github.com/kmrsandeep1998/ToonPrompt"
  url "https://github.com/kmrsandeep1998/ToonPrompt/archive/refs/tags/v0.1.0a2.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SHA256"
  license "MIT"

  depends_on "python@3.12"

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/source/p/pyyaml/pyyaml-6.0.2.tar.gz"
    sha256 "d584d9ec91ad65861cc08d42e834324ef890a082e591037abe114850ff7bbc3e"
  end

  resource "tomli" do
    url "https://files.pythonhosted.org/packages/source/t/tomli/tomli-2.0.1.tar.gz"
    sha256 "de526c12914f0c550d15924c62d72abc48d6fe7364aa87328337a31007fe8a4f"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "0.", shell_output("#{bin}/toon version")
  end
end
