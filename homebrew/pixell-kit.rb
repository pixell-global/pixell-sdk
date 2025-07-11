class PixellKit < Formula
  include Language::Python::Virtualenv

  desc "Lightweight developer kit for packaging AI agents into portable APKG files"
  homepage "https://github.com/pixell-global/pixell-kit"
  url "https://files.pythonhosted.org/packages/source/p/pixell-kit/pixell-kit-0.1.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"  # This will be updated with actual SHA256 on release
  license "Apache-2.0"
  head "https://github.com/pixell-global/pixell-kit.git", branch: "main"

  depends_on "python@3.11"

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.7.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic/pydantic-2.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/PyYAML-6.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "jsonschema" do
    url "https://files.pythonhosted.org/packages/source/j/jsonschema/jsonschema-4.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "fastapi" do
    url "https://files.pythonhosted.org/packages/source/f/fastapi/fastapi-0.100.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "uvicorn" do
    url "https://files.pythonhosted.org/packages/source/u/uvicorn/uvicorn-0.23.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "watchdog" do
    url "https://files.pythonhosted.org/packages/source/w/watchdog/watchdog-3.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/source/p/python-dotenv/python-dotenv-1.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "tabulate" do
    url "https://files.pythonhosted.org/packages/source/t/tabulate/tabulate-0.9.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "jinja2" do
    url "https://files.pythonhosted.org/packages/source/J/Jinja2/Jinja2-3.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"pixell", "--version"
    
    # Test creating a new agent project
    testpath = Pathname.new(File.join(Dir.tmpdir, "test_agent"))
    system bin/"pixell", "init", testpath
    assert_predicate testpath/"agent.yaml", :exist?
  end
end