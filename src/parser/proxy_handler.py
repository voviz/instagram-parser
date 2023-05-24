class ProxyHandler:
    @staticmethod
    def convert_to_aiohttp_format(proxy: str) -> str:
        """
        from format like ip:port:login:password -> http://login:password@ip:port
        """
        proxy_parts = proxy.split(':')
        new_format = f'http://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}'
        return new_format
