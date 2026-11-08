"""程序入口：只负责启动，所有逻辑都在 cli 层。"""

import sys

from cli import main


if __name__ == "__main__":
    sys.exit(main())
