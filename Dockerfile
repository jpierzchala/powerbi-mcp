FROM python:3.11-slim

# Install .NET runtime for pythonnet/pyadomd
RUN apt-get update && \
    apt-get install -y --no-install-recommends gnupg wget ca-certificates unzip && \
    wget -q https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    rm packages-microsoft-prod.deb && \
    apt-get update && \
    apt-get install -y --no-install-recommends dotnet-runtime-8.0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    mkdir -p /usr/lib/adomd && \
    wget -q https://www.nuget.org/api/v2/package/Microsoft.AnalysisServices.AdomdClient.netcore.retail.amd64/19.12.7-preview -O /tmp/adomd.nupkg && \
    unzip -q /tmp/adomd.nupkg -d /usr/lib/adomd && \
    rm /tmp/adomd.nupkg && \
    wget -q https://www.nuget.org/api/v2/package/Microsoft.Identity.Client/4.6.0 -O /tmp/msal.nupkg && \
    unzip -q /tmp/msal.nupkg -d /tmp/msal && \
    cp /tmp/msal/lib/netcoreapp2.1/Microsoft.Identity.Client.dll /usr/lib/adomd/lib/netcoreapp3.0/ && \
    rm -rf /tmp/msal /tmp/msal.nupkg

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
