import time
import os
import argparse
from typing import BinaryIO, AnyStr, Union

class CorruptedFile(Exception):
    pass

class Archiver:
    def __init__(self, archive_filename: str) -> None:
        self.archive_filename = archive_filename

    def encode_rle(self, archive_file: BinaryIO, file_to_encode: BinaryIO, unit_size: int) -> int:
        max_count = 255  # we only encode the count in one byte
        buf = b''        # we only hold a limited buffer in memory and avoid reading the whole file
        encoded_size = 0
        while True:
            # first we fill the buffer from the file with enough data to be able to encode 255 units (255 * unit_size bytes)
            if len(buf) < max_count * unit_size:
                buf += file_to_encode.read(max_count * unit_size - len(buf))
            if len(buf) == 0:
                return encoded_size
            # at the end of the file if the remaining bytes are not divided by unit_size pad with zeros
            r = len(buf) % unit_size
            if r != 0:
                buf += b'\0' * (unit_size - r)
            count = 1
            j = 0
            while j + unit_size < len(buf):
                if buf[j: j + unit_size] == buf[j + unit_size: j + 2 * unit_size]:  # and count < max_count: not needed because buf is never larger
                    count += 1
                    j += unit_size
                else:
                    break
            encoded_size += archive_file.write(count.to_bytes(1, byteorder='big'))
            encoded_size += archive_file.write(buf[:unit_size])
            buf = buf[(unit_size * count):]  # trim buf

    def decode_rle(self, archive_file: BinaryIO, file_to_decode: Union[BinaryIO, None], unit_size: int, encoded_size: int, original_file_size: int)-> None:
        while encoded_size > 0:
            b = archive_file.read(1)
            if len(b) < 1:
                raise CorruptedFile
            count = int.from_bytes(b, byteorder='big')
            data = archive_file.read(unit_size)
            if len(data) < unit_size:
                raise CorruptedFile
            if original_file_size < unit_size:
                if file_to_decode != None:
                    file_to_decode.write(data[:original_file_size])
                break
            if file_to_decode != None:
                file_to_decode.write(data * count)
            encoded_size -= unit_size + 1
            original_file_size -= unit_size * count

    def add_file(self, file_name: AnyStr, unit_size: int) -> bool:
        try:
            start_time = time.time()
            # because we are using seek() below, and it does not work in Windows in append mode,
            # we use either 'r+' or 'w', depending on whether the file exists or not.
            # this is why we don't use "with" in this function and have to explicitly call close()
            try:
                archive_file = open(self.archive_filename, 'rb+')
                archive_file.seek(0, os.SEEK_END)
            except FileNotFoundError:
                archive_file = open(self.archive_filename, 'wb')
            base_name = os.path.basename(file_name).encode()
            archive_file.write(len(base_name).to_bytes(2, byteorder='big'))
            archive_file.write(base_name)
            original_file_size = os.path.getsize(file_name)
            archive_file.write(original_file_size.to_bytes(8, byteorder='big'))
            archive_file.write(unit_size.to_bytes(1, byteorder='big'))
            pos = archive_file.tell()
            encoded_size = 0
            archive_file.write(encoded_size.to_bytes(8, byteorder='big'))
            with open(file_name, 'rb') as file_to_encode:
                encoded_size = self.encode_rle(archive_file, file_to_encode, unit_size)
                archive_file.seek(pos)
                archive_file.write(encoded_size.to_bytes(8, byteorder='big'))
                archive_file.seek(0, os.SEEK_END)
            archive_file.close()
            end_time = time.time()
            encoding_time = end_time - start_time
            print(f'File name: {file_name} '
                  f'Time encoding: {encoding_time:.2f} seconds '
                  f'Unit size: {unit_size} '
                  f'Encode ratio: {encoded_size / original_file_size:.2%}')
        except Exception as e:
            print(e)
            return False
        return True

    def find_valid_file_name(self, output_directory: str, file_name: str) -> str:
        base, ext = os.path.splitext(os.path.join(output_directory, file_name))
        i = 0
        while True:
            if i == 0:
                new_name = base + ext
            else:
                new_name = base + '_' + str(i) + ext
            if not os.path.exists(new_name):
                return new_name
            i += 1

    def extract_metadata(self, archive_file: BinaryIO) -> tuple[str, int, int, int]:
        b = archive_file.read(2)
        if len(b) < 2:
            raise CorruptedFile
        file_name_length = int.from_bytes(b, byteorder='big')
        b = archive_file.read(file_name_length)
        if len(b) < file_name_length:
            raise CorruptedFile
        file_name = b.decode()
        b = archive_file.read(8)
        if len(b) < 8:
            raise CorruptedFile
        original_file_size = int.from_bytes(b, byteorder='big')
        b = archive_file.read(1)
        if len(b) < 1:
            raise CorruptedFile
        unit_size = int.from_bytes(b, byteorder='big')
        b = archive_file.read(8)
        if len(b) < 8:
            raise CorruptedFile
        encoded_file_size = int.from_bytes(b, byteorder='big')
        return file_name, unit_size, encoded_file_size, original_file_size

    def extract_all(self, output_directory: str) -> None:
        try:
            os.makedirs(output_directory, exist_ok=True)
            file_size = os.path.getsize(self.archive_filename)
            with open(self.archive_filename, 'rb') as archive_file:
                while True:
                    if archive_file.tell() == file_size:
                        return
                    start_time = time.time()
                    file_name, unit_size, encoded_file_size, original_file_size = self.extract_metadata(archive_file)
                    output_filename = self.find_valid_file_name(output_directory, file_name)
                    with open(output_filename, 'wb') as file_to_decode:
                        self.decode_rle(archive_file, file_to_decode, unit_size, encoded_file_size, original_file_size)
                    end_time = time.time()
                    print(f'File name: {file_name} '
                          f'Decoded into: {output_filename} '
                          f'Decode time: {end_time - start_time:.2f} seconds')
        except CorruptedFile:
            print(f"{self.archive_filename} is corrupted.")
        except Exception as e:
            print(e)

    def test_all(self) -> None:
        try:
            file_size = os.path.getsize(self.archive_filename)
            with open(self.archive_filename, 'rb') as archive_file:
                while True:
                    if archive_file.tell() == file_size:
                        break
                    _, unit_size, encoded_file_size, original_file_size = self.extract_metadata(archive_file)
                    self.decode_rle(archive_file, None, unit_size, encoded_file_size, original_file_size)
        except CorruptedFile:
            print(f"{self.archive_filename} is corrupted.")
        except Exception as e:
            print(e)
        else:
            print(f"{self.archive_filename} is valid.")

    def list_all(self) -> None:
        try:
            file_size = os.path.getsize(self.archive_filename)
            with open(self.archive_filename, 'rb') as archive_file:
                while True:
                    if archive_file.tell() == file_size:
                        break
                    file_name, unit_size, encoded_file_size, original_file_size = self.extract_metadata(archive_file)
                    archive_file.seek(encoded_file_size, os.SEEK_CUR)
                    print(f'File name: {file_name} '
                          f'Unit size: {unit_size} '
                          f'Encoded file size: {encoded_file_size} '
                          f'Original file size: {original_file_size} '
                          f'Encode ratio: {encoded_file_size / original_file_size:.2%}')
        except CorruptedFile:
            print(f"{self.archive_filename} is corrupted.")
        except Exception as e:
            print(e)

def main():
    parser = argparse.ArgumentParser(description="Archive files using RLE encoding")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-c", "--compress", action="store_true", help="Compress files")
    group.add_argument("-d", "--decompress", action="store_true", help="Decompress files")
    group.add_argument("-t", "--test", action="store_true", help="Test the archive")
    group.add_argument("-l", "--list", action="store_true", help="List the archive content")
    parser.add_argument("-u", "--unit_size", type=int, default=1, help="Size of encoding unit")
    parser.add_argument("archive_filename", help="Name of the archive file")
    parser.add_argument("files", nargs="*", help="Files to compress or output directory to decompress")
    args = parser.parse_args()
    archiver = Archiver(args.archive_filename)

    if args.compress:
        if args.unit_size == 0 or args.unit_size > 16:
            print("Error: unit size must be between 1 and 16")
            return
        for path in args.files:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for f in files:
                        if not archiver.add_file(os.path.join(root, f), args.unit_size):
                            print(f"Failed to compress {f}. Aborting")
                            return
            else:
                if not archiver.add_file(path, args.unit_size):
                    print(f"Failed to compress {path}. Aborting")
                    return
    elif args.decompress:
        if len(args.files) != 1:
            print("Please provide exactly one output directory for decompression.")
        else:
            archiver.extract_all(args.files[0])
    elif args.test:
        if len(args.files) != 0:
            print("Too many arguments.")
        else:
            archiver.test_all()
    elif args.list:
        if len(args.files) != 0:
            print("Too many arguments.")
        else:
            archiver.list_all()

if __name__ == "__main__":
    main()
