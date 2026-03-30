"""
自己署名SSL証明書の生成スクリプト
スマホからHTTPSでカメラを使うために必要
"""
import os
import ipaddress
import datetime


def generate_cert(cert_path="cert.pem", key_path="key.pem"):
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        print("[ERROR] cryptography パッケージが見つかりません")
        print("  pip install cryptography を実行してください")
        return False

    # 既に存在する場合はスキップ
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"[INFO] SSL証明書は既に存在します: {cert_path}")
        return True

    print("[INFO] SSL証明書を生成中...")

    # 秘密鍵の生成
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # PCのIPアドレスを取得（複数の方法を試みる）
    import socket
    local_ips = set()

    # 方法1: ルーティングから送信元IPを確認（最も確実）
    for target in ("8.8.8.8", "1.1.1.1"):
        try:
            with socket.create_connection((target, 80), timeout=1) as s:
                ip = s.getsockname()[0]
                if not ip.startswith("127.") and ":" not in ip:
                    local_ips.add(ip)
            break
        except Exception:
            pass

    # 方法2: ホスト名から取得
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if not ip.startswith("127.") and ":" not in ip:
                local_ips.add(ip)
    except Exception:
        pass

    # 方法3: hostname -I コマンド（Linux）
    try:
        import subprocess
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=2)
        for ip in result.stdout.split():
            if not ip.startswith("127.") and ":" not in ip:
                local_ips.add(ip)
    except Exception:
        pass

    local_ips = list(local_ips)

    # 証明書の作成
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"Shipping-Management"),
    ])

    san_list = [
        x509.DNSName(u"localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    for ip in local_ips:
        try:
            san_list.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
            print(f"[INFO] SAN に追加: {ip}")
        except Exception:
            pass

    if not local_ips:
        print("[WARNING] LAN IPアドレスが取得できませんでした (localhost 専用の証明書を生成)")

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[INFO] 証明書生成完了: {cert_path}, {key_path}")
    if local_ips:
        print()
        print("=" * 50)
        print("  スマホからのアクセスURL:")
        for ip in local_ips:
            print(f"    https://{ip}:8443")
        print()
        print("  ※ 初回は証明書の警告が出ます")
        print("     Chrome : 詳細設定 → アクセスする")
        print("     Safari : 詳細を表示 → このWebサイトを閲覧")
        print("=" * 50)
    return True


if __name__ == "__main__":
    import sys
    ok = generate_cert()
    sys.exit(0 if ok else 1)
