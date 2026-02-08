import subprocess
import shlex



def run_command(input_command: str, cwd='.') -> str:

    if input_command.strip() == '':
        return ''

    arg_list = shlex.split(input_command)

    
    result = subprocess.run(
        arg_list,
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd

    )

    return result.stdout



if __name__ == "__main__":
    command = "echo Hello, World!"
    output = run_command(command)
    print(f"Command Output: {output}")
