FROM python:3.11-slim

# Install .NET runtime and ADOMD.NET libraries
COPY scripts/install_dotnet_adomd.sh /tmp/install_dotnet_adomd.sh

RUN sed -i 's/\r$//' /tmp/install_dotnet_adomd.sh \
 && chmod +x /tmp/install_dotnet_adomd.sh \
 && bash /tmp/install_dotnet_adomd.sh --system \
 && rm /tmp/install_dotnet_adomd.sh

# Configure pythonnet to use the installed .NET runtime
ENV DOTNET_ROOT=/usr/share/dotnet \
    PYTHONNET_RUNTIME=coreclr \
    ADOMD_LIB_DIR=/usr/lib/adomd/lib/netcoreapp3.0 \
    PATH="$PATH:/usr/share/dotnet"

WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "src/server.py"]
