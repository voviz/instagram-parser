import os
import tempfile

from parser.exceptions import InvalidProxyFormatError


class ProxyHandler:
    @staticmethod
    def convert_to_aiohttp_format(proxy: str) -> str:
        """
        convert to format -> http://login:password@ip:port
        """
        try:
            # split proxy to the parts
            if '@' in proxy:
                proxy = proxy.lstrip('http://').split('@')
                proxy_parts = []
                proxy_parts.extend(proxy[0].split(':'))
                proxy_parts.extend(proxy[1].split(':'))
            else:
                proxy_parts = proxy.lstrip('http://').split(':')
            # check each part
            for part in proxy_parts:
                if part.isdigit():
                    port = part
                elif '.' in part:
                    ip = part
            if proxy_parts.index(ip) == 2 and proxy_parts.index(port) == 3:
                login, password = proxy_parts[0], proxy_parts[1]
            else:
                login, password = proxy_parts[2], proxy_parts[3]
        except Exception:
            raise InvalidProxyFormatError(proxy)

        return f'http://{login}:{password}@{ip}:{port}'

    @staticmethod
    def convert_to_seleniumbase_format(proxy: str) -> str:
        """
        convert to format -> login:password@ip:port
        """
        try:
            # split proxy to the parts
            if '@' in proxy:
                proxy = proxy.lstrip('http://').split('@')
                proxy_parts = []
                proxy_parts.extend(proxy[0].split(':'))
                proxy_parts.extend(proxy[1].split(':'))
            else:
                proxy_parts = proxy.lstrip('http://').split(':')
            # check each part
            for part in proxy_parts:
                if part.isdigit():
                    port = part
                elif '.' in part:
                    ip = part
            if proxy_parts.index(ip) == 2 and proxy_parts.index(port) == 3:
                login, password = proxy_parts[0], proxy_parts[1]
            else:
                login, password = proxy_parts[2], proxy_parts[3]
        except Exception:
            raise InvalidProxyFormatError(proxy)

        return f'{login}:{password}@{ip}:{port}'


class SeleniumProxyHandler:
    """Proxy format for selenium webdriver."""

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "76.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: %d
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        { urls: ["<all_urls>"] },
        ['blocking']
    );
    """

    def __init__(self, host, port, user, password):
        self._dir = os.path.normpath(tempfile.mkdtemp())

        manifest_file = os.path.join(self._dir, "manifest.json")
        with open(manifest_file, mode="w") as f:
            f.write(self.manifest_json)

        background_js = self.background_js % (host, port, user, password)
        background_file = os.path.join(self._dir, "background.js")
        with open(background_file, mode="w") as f:
            f.write(background_js)

    @property
    def directory(self):
        return self._dir

    def __del__(self):
        import shutil
        shutil.rmtree(self._dir)

    @staticmethod
    def convert_to_selenium_format(proxy: str) -> tuple:
        """
        from format like ip:port:login:password -> http://login:password@ip:port
        """
        try:
            # split proxy to the parts
            if '@' in proxy:
                proxy = proxy.lstrip('http://').split('@')
                proxy_parts = []
                proxy_parts.extend(proxy[0].split(':'))
                proxy_parts.extend(proxy[1].split(':'))
            else:
                proxy_parts = proxy.lstrip('http://').split(':')
            # check each part
            for part in proxy_parts:
                if part.isdigit():
                    port = part
                elif '.' in part:
                    ip = part
            if proxy_parts.index(ip) == 2 and proxy_parts.index(port) == 3:
                login, password = proxy_parts[0], proxy_parts[1]
            else:
                login, password = proxy_parts[2], proxy_parts[3]
        except Exception:
            raise InvalidProxyFormatError(proxy)

        return ip, int(port), login, password