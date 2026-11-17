import { createRequestHandler } from "@react-router/express";
import compression from "compression";
import express from "express";

const port = Number(process.env.PORT ?? 3000);

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
app.use(compression());
app.use("/assets", express.static("build/client/assets", { immutable: true, maxAge: "1y" }));
app.use(express.static("build/client", { maxAge: "1h" }));
app.all("/{*splat}", createRequestHandler({ build: await import("./build/server/index.js") }));

app.listen(port, () => console.log(`Frontend listening on port ${port}`));
