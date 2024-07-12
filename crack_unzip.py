import multiprocessing
import os
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

seven_zip_dir = '7-Zip'  # 根据你的实际安装路径调整

dictionary_urls = {
    "1": "https://raw.githubusercontent.com/jerryyang-git/compressed_password_book/main/galgame-Password.txt",
    "0": "选择后输入本地txt文件路径或者其他网络文件路径"
}

dictionary_names = {
    "1": "Galgame-Password",
    "0": "输入本地txt文件路径或者其他网络文件路径"
}


def download_dictionary(url, save_path):
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 KB
        with open(save_path, 'wb') as f, tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
            for data in response.iter_content(block_size):
                f.write(data)
                pbar.update(len(data))
        return True
    except requests.exceptions.RequestException as e:
        print(f"下载字典文件失败: {e}")
        return False


def test_password(file_path, dictionary_path, password):
    seven_zip_executable = os.path.join(seven_zip_dir, '7z.exe')
    command_to_run = [seven_zip_executable, 't', file_path, f'-p{password}']
    result = subprocess.run(command_to_run, capture_output=True, text=True)
    return result.stdout


def run_7zip_multithread(file_path, dictionary_path, passwords):
    results = {}
    max_workers = multiprocessing.cpu_count()  # 获取计算机核心数
    with ThreadPoolExecutor(max_workers) as executor:
        futures = {executor.submit(test_password, file_path, dictionary_path, password.strip()): password.strip() for password in passwords}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Running dictionary"):
            password = futures[future]
            results[password] = future.result()
            if "Everything is Ok" in results[password] and "No files to process" not in results[password] and "Wrong password" not in results[password]:
                # 发现正确密码后，取消剩余任务
                for f in futures:
                    f.cancel()
                return password
    return None


def main():
    while True:
        file_path = input("请输入需要测试的压缩包文件路径: ")

        if not os.path.exists(file_path):
            print("输入的文件路径不存在，请重新输入。")
            continue

        print("请选择一个字典文件:")
        for key, value in dictionary_names.items():
            print(f"{key}: {value}")

        choice = input("请输入选项编号: ").strip()
        if choice not in dictionary_urls:
            print("无效的选项，请重新选择。")
            continue

        dictionary_url = dictionary_urls[choice]
        if choice == "0":
            dictionary_url = input("请输入本地txt文件路径或者其他网络文件路径: ").strip()

        dictionary_path = 'dictionary.txt'
        if dictionary_url.startswith("http"):
            print("正在下载字典文件...")
            if not download_dictionary(dictionary_url, dictionary_path):
                print("下载字典文件失败，请检查您的网络")
                continue
        else:
            if not os.path.exists(dictionary_url):
                print("输入的字典文件路径不存在，请重新输入。")
                continue
            dictionary_path = dictionary_url

        with open(dictionary_path, 'r', encoding='utf-8') as dict_file:
            passwords = dict_file.readlines()

        print("开始跑字典...")
        password = run_7zip_multithread(file_path, dictionary_path, passwords)
        if password:
            print(f"找到了正确的密码: {password}")
        else:
            print("没有找到正确的密码。")

        choice = input("是否要测试另一个文件？(yes/no): ").strip().lower()
        if choice != 'yes':
            break

    input("Press Enter to close...")


if __name__ == '__main__':
    main()
