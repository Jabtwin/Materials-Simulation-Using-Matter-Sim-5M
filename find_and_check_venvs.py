import os
import subprocess
import sys

def main():
    print("=" * 60)
    print("TÌM KIẾM CÁC MÔI TRƯỜNG ẢO (VIRTUAL ENVIRONMENTS)")
    print("Quá trình này có thể mất vài phút. Vui lòng chờ...")
    print("=" * 60)

    # Bắt đầu tìm từ thư mục User hiện tại (ví dụ C:\Users\hm-gpham)
    user_dir = os.environ.get("USERPROFILE", "C:\\")
    
    # Bỏ qua các thư mục hệ thống hoặc quá nặng để quét nhanh hơn
    exclude_dirs = {
        'AppData', 'Application Data', 'Local Settings', 'Windows', 
        'Program Files', 'Program Files (x86)', '.cache', 'node_modules',
        '.git', 'anaconda3', 'miniconda3'
    }
    
    found_venvs = []
    
    print(f"Đang quét thư mục: {user_dir}")
    
    # Quét các thư mục
    for root, dirs, files in os.walk(user_dir):
        # Lọc bỏ các thư mục không cần thiết
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for d in dirs:
            # Tìm các thư mục có tên thường dùng cho môi trường ảo
            if d.lower() in ['.venv', 'venv', 'env', 'mattersim_env']:
                venv_path = os.path.join(root, d)
                python_exe = os.path.join(venv_path, "Scripts", "python.exe")
                # Nếu có file python.exe bên trong Scripts thì đích thị là venv
                if os.path.exists(python_exe):
                    found_venvs.append(venv_path)

    if not found_venvs:
        print("\n[!] Không tìm thấy môi trường ảo nào (không có thư mục .venv, venv).")
        input("Nhấn Enter để thoát...")
        return

    print(f"\n[OK] Đã tìm thấy {len(found_venvs)} môi trường ảo!")
    print("-" * 60)
    
    best_venv = None

    for venv in found_venvs:
        print(f"\nĐang kiểm tra: {venv}")
        python_exe = os.path.join(venv, "Scripts", "python.exe")
        
        # Thử xem có thư viện mattersim không
        try:
            result = subprocess.run(
                [python_exe, "-c", "import mattersim; print('MATTERSIM_FOUND')"],
                capture_output=True, text=True, timeout=10
            )
            if "MATTERSIM_FOUND" in result.stdout:
                print("  => [HOÀN HẢO] Môi trường này CÓ cài đặt mattersim!")
                best_venv = venv
            else:
                print("  => [KHÔNG CÓ] Môi trường này KHÔNG có mattersim.")
        except Exception as e:
            print("  => [LỖI] Không thể kiểm tra môi trường này.")

    print("\n" + "=" * 60)
    if best_venv:
        print("KẾT LUẬN: ĐÃ TÌM THẤY MÔI TRƯỜNG ẢO CHUẨN CỦA DỰ ÁN!")
        print(f"Đường dẫn: {best_venv}")
        print("\nĐể sử dụng nó, bạn hãy gõ lệnh sau vào PowerShell:")
        print(f"& '{best_venv}\\Scripts\\Activate.ps1'")
    else:
        print("KẾT LUẬN: Các môi trường ảo tìm được đều chưa cài mattersim.")
        print("Bạn sẽ cần cài đặt lại các thư viện cho thư mục bạn muốn.")
    print("=" * 60)
    
    input("Nhấn Enter để kết thúc...")

if __name__ == "__main__":
    main()
