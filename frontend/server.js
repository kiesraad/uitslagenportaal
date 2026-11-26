import { createRequestHandler } from "@react-router/express";
import compression from "compression";
import express from "express";

const port = Number(process.env.PORT ?? 3000);

// Pages fetch their data from the backend while rendering; without its address every page fails.
if (!process.env.SSR_API_ORIGIN) {
   console.error("SSR_API_ORIGIN is not set; set it to the backend's origin, e.g. http://localhost:8080");
   process.exit(1);
}

// Same keys as the backend's JSON logs, so Alloy and Grafana treat both alike.
function accessLog(req, res, next) {
   const start = process.hrtime.bigint();
   res.on("finish", () => {
      const { statusCode: status } = res;
      // Successful kubelet probes arrive every few seconds; a failing one is exactly what to keep.
      if (status < 400 && req.get("user-agent")?.startsWith("kube-probe/")) return;
      const durationMs = Math.round(Number(process.hrtime.bigint() - start) / 1e6);
      const levelname = status >= 500 ? "ERROR" : status >= 400 ? "WARNING" : "INFO";
      console.log(
         JSON.stringify({
            time: new Date().toISOString(),
            levelname,
            name: "frontend.access",
            message: `${req.method} ${req.originalUrl} ${status} ${durationMs}ms`,
            method: req.method,
            path: req.originalUrl,
            status,
            duration_ms: durationMs,
         }),
      );
   });
   next();
}

const app = express();
app.disable("x-powered-by");
app.use(accessLog);
// Pages need the backend; the probes should not take the frontend down with it.
app.get("/healthz", (_req, res) => res.sendStatus(200));
app.use(compression());
app.use("/assets", express.static("build/client/assets", { immutable: true, maxAge: "1y" }));
// A missing asset is a 404, not a page.
app.use("/assets", (_req, res) => res.sendStatus(404));
app.use(express.static("build/client", { maxAge: "1h" }));
app.all("/{*splat}", createRequestHandler({ build: await import("./build/server/index.js") }));

app.listen(port, () => console.log(`Frontend listening on port ${port}`));
