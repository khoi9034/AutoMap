import net from "node:net";

const FRONTEND_PORT = Number.parseInt(process.env.PORT || "3010", 10);
const BACKEND_PORT = Number.parseInt(process.env.BACKEND_PORT || "8010", 10);
const RESERVED_PORTS = new Set([3000, 8000]);
const RESERVED_WARNING = "Ports 3000 and 8000 are reserved for Cabarrus FutureScape.";

function isPortBusy(port, host = "127.0.0.1") {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(250);
    socket.once("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.once("timeout", () => {
      socket.destroy();
      resolve(false);
    });
    socket.once("error", () => {
      socket.destroy();
      resolve(false);
    });
    socket.connect(port, host);
  });
}

async function main() {
  if (RESERVED_PORTS.has(FRONTEND_PORT)) {
    console.error(`${RESERVED_WARNING} AutoMap frontend cannot bind to port ${FRONTEND_PORT}.`);
    process.exit(1);
  }
  if (RESERVED_PORTS.has(BACKEND_PORT)) {
    console.error(`${RESERVED_WARNING} AutoMap backend/API cannot bind to port ${BACKEND_PORT}.`);
    process.exit(1);
  }

  for (const reservedPort of [...RESERVED_PORTS].sort()) {
    if (await isPortBusy(reservedPort)) {
      console.warn(`Warning: ${RESERVED_WARNING} Detected port ${reservedPort} in use.`);
    }
  }

  if (await isPortBusy(FRONTEND_PORT)) {
    console.error(`AutoMap frontend port ${FRONTEND_PORT} is already in use.`);
    process.exit(1);
  }

  console.log(`AutoMap frontend port guard passed. Frontend=${FRONTEND_PORT}; backend/API=${BACKEND_PORT}.`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
