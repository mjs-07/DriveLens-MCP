from src.drivelens.services.drive import get_drive_service


def main():
    drive = get_drive_service()

    response = (
        drive.files()
        .list(
            pageSize=10,
            fields="files(id,name,mimeType,modifiedTime,size)",
        )
        .execute()
    )

    files = response.get("files", [])

    print()
    print(f"Google Drive API: SUCCESS")
    print(f"Files returned: {len(files)}")
    print()

    for file in files:
        print(
            f"- {file.get('name')} "
            f"[{file.get('mimeType')}] "
            f"id={file.get('id')}"
        )


if __name__ == "__main__":
    main()