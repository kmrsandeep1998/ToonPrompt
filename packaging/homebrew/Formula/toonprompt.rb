class Toonprompt < Formula
  desc "Universal prompt optimization wrapper for AI coding CLIs"
  homepage "https://github.com/kmrsandeep1998/ToonPrompt"
  url "https://github.com/kmrsandeep1998/ToonPrompt/archive/refs/tags/v0.1.0a2.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SHA256"
  license "MIT"

  depends_on "python@3.12"

  def install
    system "pip3", "install", "--prefix=#{prefix}", "."
  end

  test do
    assert_match "0.", shell_output("#{bin}/toon version")
  end
end
