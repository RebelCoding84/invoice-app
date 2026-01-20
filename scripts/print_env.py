import platform
import sys


def main() -> None:
    print(sys.version)
    print(sys.executable)
    print(platform.platform())
    print(platform.python_version())


if __name__ == "__main__":
    main()
