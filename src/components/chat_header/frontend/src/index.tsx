import React from "react";
import ReactDOM from "react-dom/client";

declare global { interface Window { Streamlit?: any; } }

const Root: React.FC = () => {
  const [args, setArgs] = React.useState<any>({ title: "Introducing GPT-5", subtitle: "", gradient: true });
  const [closed, setClosed] = React.useState(false);

  React.useEffect(() => {
    const onRender = (event: any) => {
      setArgs(event.detail?.args || {});
      window.Streamlit?.setFrameHeight?.(closed ? 0 : 220);
    };
    window.addEventListener("streamlit:render", onRender);
    return () => window.removeEventListener("streamlit:render", onRender);
  }, [closed]);

  if (closed) return null;

  return (
    <div className="hero-wrap">
      <div className="hero-bg" />
      <div className="hero-content">
        <div className="hero-title">{args.title}</div>
        {args.subtitle && <div className="hero-sub">{args.subtitle}</div>}
        <div>
          <span className="hero-cta">Learn more</span>
        </div>
        <button className="hero-close" onClick={() => setClosed(true)}>Close</button>
      </div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById("root")!).render(<Root />);