import { Outlet } from "react-router";

/** Route module for a path level that only carries parameters and has no page of its own. */
export default function RouteOutlet() {
   return <Outlet />;
}
