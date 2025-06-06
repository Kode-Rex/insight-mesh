import subprocess
from rich.console import Console

console = Console()

def run_command(command, verbose=False):
    """Run a shell command and return the result"""
    try:
        if verbose:
            console.print(f"[bold blue]Running:[/bold blue] {' '.join(command)}")
            
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[bold red]Error:[/bold red] {result.stderr}")
            return False
            
        if verbose and result.stdout:
            console.print(result.stdout)
            
        return True
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return False
        
def extract_urls(ports_string):
    """Extract URLs from Docker port mappings"""
    urls = []
    if not ports_string:
        return urls
    
    for port_mapping in ports_string.split(','):
        if '->' in port_mapping and 'tcp' in port_mapping:
            try:
                host_part = port_mapping.split('->')[0].strip()
                if ':' in host_part:
                    host, port = host_part.split(':')
                    # Replace 0.0.0.0 with localhost
                    if host == '0.0.0.0':
                        host = 'localhost'
                    urls.append(f"http://{host}:{port}")
                else:
                    port = host_part
                    urls.append(f"http://localhost:{port}")
            except Exception:
                pass
    return urls 