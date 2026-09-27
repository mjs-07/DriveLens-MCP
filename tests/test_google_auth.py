from src.drivelens.auth.oauth import get_credentials


def main():
    credentials = get_credentials()

    print()
    print("Google OAuth: SUCCESS")
    print(f"Token valid: {credentials.valid}")
    print(f"Token expired: {credentials.expired}")
    print(f"Scopes: {credentials.scopes}")


if __name__ == "__main__":
    main()