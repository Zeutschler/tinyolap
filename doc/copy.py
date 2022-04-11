# purpose - Copy all file from the folder '/doc/build/html'
#           to the folder '/tinyolap.com/docs'.
import os
from distutils.dir_util import remove_tree, copy_tree


def main():
    root = os.path.abspath(os.path.dirname(__file__))
    copy_source = os.path.join(root, "build", "html")
    copy_destination = os.path.join(os.path.dirname(root), "tinyolap.com", "docs")

    print(f"Copying files from '{copy_source}' to '{copy_destination}'")
    print(f"\t...cleaning destination folder by deleting all files in '{copy_destination}'.")
    if os.path.isdir(copy_destination):
        remove_tree(copy_destination, verbose=1)

    print(f"\t...copying files to destination folder '{copy_destination}'.")
    copy_tree(copy_source, copy_destination, verbose=1)
    print(f"\t...we're done!")


if __name__ == "__main__":
    main()
