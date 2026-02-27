"""
Server 配置加载单元测试
"""

import os
from unittest.mock import patch

import pytest


class TestLoadConfig:
    """测试配置加载逻辑"""

    def test_env_vars_override_file(self, tmp_path):
        """环境变量优先于配置文件"""
        env = {
            "GITHUB_TOKEN": "env-token",
            "GITHUB_OWNER": "env-owner",
            "SLACK_BOT_TOKEN": "env-slack-token",
            "SLACK_DEFAULT_CHANNEL": "#env-channel",
        }
        with patch.dict(os.environ, env, clear=False):
            # 导入时会读取配置
            from server import load_config
            config = load_config()
            assert config["github"]["token"] == "env-token"
            assert config["github"]["owner"] == "env-owner"
            assert config["slack"]["bot_token"] == "env-slack-token"

    def test_missing_github_token_raises(self):
        """缺少 GitHub Token 应抛出异常"""
        env = {
            "GITHUB_TOKEN": "",
            "SLACK_BOT_TOKEN": "some-token",
        }
        with patch.dict(os.environ, env, clear=False):
            from server import load_config
            # 清空可能存在的 config.yaml 影响
            with patch("server.Path.exists", return_value=False):
                with pytest.raises(ValueError, match="GitHub Token"):
                    load_config()

    def test_missing_slack_token_raises(self):
        """缺少 Slack Token 应抛出异常"""
        env = {
            "GITHUB_TOKEN": "some-token",
            "SLACK_BOT_TOKEN": "",
        }
        with patch.dict(os.environ, env, clear=False):
            from server import load_config
            with patch("server.Path.exists", return_value=False):
                with pytest.raises(ValueError, match="Slack"):
                    load_config()
