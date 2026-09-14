/**
 * Streamlit Components v2 React entry point.
 *
 * Mounts the custom studio React application inside Streamlit's iframe host.
 * Uses a WeakMap to memoize React roots across Streamlit script reruns without
 * leaking memory or remounting DOM trees unnecessarily.
 * Next module to read: `StudioComponent.tsx` for the view dispatcher.
 */

import type {
  FrontendRenderer,
  FrontendRendererArgs,
} from "@streamlit/component-v2-lib";
import { createRoot, type Root } from "react-dom/client";

import StudioComponent, { type StudioData } from "./StudioComponent";
import "./style.css";

// WeakMap caches React 18 createRoot instances keyed by the parent DOM container
// so Streamlit iframe updates reuse existing component instances without flashing.
const roots = new WeakMap<FrontendRendererArgs["parentElement"], Root>();

const StudioRoot: FrontendRenderer<Record<string, never>, StudioData> = ({

  data,
  parentElement,
}) => {
  const mount = parentElement.querySelector(".react-root");
  if (!(mount instanceof HTMLElement)) {
    throw new Error("Component mount was not found");
  }

  let root = roots.get(parentElement);
  if (!root) {
    root = createRoot(mount);
    roots.set(parentElement, root);
  }
  root.render(<StudioComponent data={data} />);

  return () => {
    roots.get(parentElement)?.unmount();
    roots.delete(parentElement);
  };
};

export default StudioRoot;
