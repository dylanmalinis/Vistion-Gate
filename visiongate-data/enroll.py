"""Admin CLI to enroll, list, and remove registered faces.

Examples:
    python enroll.py --add "Ali" --image ali.jpg
    python enroll.py --list
    python enroll.py --remove "Ali"

With the stub recognizer you can enroll from any file (even a non-image) so
the full pipeline is demoable without a camera. With the face_recognition
backend the image must contain exactly one detectable face.
"""

import argparse
import sys

import config
import recognizer
import store


def cmd_add(name: str, image_path: str) -> int:
    try:
        with open(image_path, "rb") as fh:
            image_bytes = fh.read()
    except OSError as exc:
        print(f"Could not read image: {exc}")
        return 1

    try:
        encoding = recognizer.make_encoding(image_bytes)
    except ValueError as exc:
        print(f"Enrollment failed: {exc}")
        return 1

    # The store holds a list of encodings per user; a file enroll gives one.
    user_id = store.add_user(name, [encoding])
    print(f"Enrolled '{name}' (user id {user_id}) using backend "
          f"'{config.RECOGNIZER_BACKEND}'.")
    return 0


def cmd_list() -> int:
    users = store.get_users()
    if not users:
        print("No registered users yet.")
        return 0
    print(f"{len(users)} registered user(s):")
    for u in users:
        print(f"  - {u['name']}  (id {u['id']}, enrolled {u['created_at']})")
    return 0


def cmd_remove(name: str) -> int:
    if store.remove_user(name):
        print(f"Removed '{name}'.")
        return 0
    print(f"No user named '{name}'.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VisionGate face enrollment tool.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--add", metavar="NAME", help="Enroll a new face under NAME.")
    group.add_argument("--list", action="store_true", help="List registered users.")
    group.add_argument("--remove", metavar="NAME", help="Remove a registered user.")
    parser.add_argument("--image", help="Path to the face image (required with --add).")

    args = parser.parse_args(argv)
    store.init_db()

    if args.add:
        if not args.image:
            parser.error("--add requires --image")
        return cmd_add(args.add, args.image)
    if args.list:
        return cmd_list()
    if args.remove:
        return cmd_remove(args.remove)
    return 0


if __name__ == "__main__":
    sys.exit(main())
