"""Utilidad de diagnóstico: imprime un único UID y no usa red ni la API."""

import time

from rfid_reader import RC522Reader


def main() -> None:
    reader = RC522Reader()
    print("Acerca una tarjeta al RC522…")
    try:
        while True:
            uid = reader.poll_uid()
            if uid:
                print(uid)
                return
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("Lectura cancelada")
    finally:
        reader.close()


if __name__ == "__main__":
    main()
