#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from image_gen_mcp.core.server import create_server


def main():
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
