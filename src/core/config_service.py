import json
import os
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    _settings = {}
    _tried_loading = False  # <--- Memory to prevent retrying forever
    PROJECT_ROOT = None
    REQUIRED_KEYS = ["FAISS_INDEX_PATH", "BM25_INDEX_PATH", "DATA_DIR", "MODEL_PATH", "RERANKER_PATH"]

    @classmethod
    def _validate_config(cls):
        """Validate that all required keys are present in config."""
        missing_keys = [key for key in cls.REQUIRED_KEYS if key not in cls._settings]
        
        if missing_keys:
            logger.warning(
                f"⚠️ Missing config keys: {missing_keys}. "
                f"These will use default values, but it's recommended to add them to config.json"
            )
        
        return len(missing_keys) == 0

    @classmethod
    def _load_once(cls):
        """Internal helper to load the config only once."""
        if cls._tried_loading:
            return

        cls._tried_loading = True

        # 1. Find where this file is and walk upward until we find config.json.
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        found_config_dir = None
        while True:
            config_path = os.path.join(curr_dir, "config.json")
            if os.path.exists(config_path):
                found_config_dir = curr_dir
                break

            parent_dir = os.path.dirname(curr_dir)
            if parent_dir == curr_dir:
                break
            curr_dir = parent_dir

        if found_config_dir is not None:
            # If config.json is inside a `src` folder, treat the parent as the project root.
            if os.path.basename(found_config_dir).lower() == "src":
                candidate_root = os.path.dirname(found_config_dir)
                cls.PROJECT_ROOT = candidate_root
            else:
                cls.PROJECT_ROOT = found_config_dir
        else:
            # Fallback to the folder above `src` if config.json isn't found.
            cls.PROJECT_ROOT = os.path.normpath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, os.pardir)
            )

        config_path = os.path.join(found_config_dir or cls.PROJECT_ROOT, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cls._settings = json.load(f)
                logger.info(f"✅ Config loaded from: {config_path}")
                # Validate the config
                cls._validate_config()
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse config.json: {e}. Using empty config.")
                cls._settings = {}
            except IOError as e:
                logger.error(f"❌ Failed to read config.json: {e}. Using empty config.")
                cls._settings = {}
        else:
            logger.warning(f"⚠️ config.json not found at {config_path}. Using empty config.")

    @classmethod
    def get(cls, key, default=None):
        """Safe getter that triggers a load if needed."""
        cls._load_once() 
        return cls._settings.get(key, default)

# Trigger the load immediately when imported
ConfigManager._load_once()