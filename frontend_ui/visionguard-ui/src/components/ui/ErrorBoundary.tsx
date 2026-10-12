import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}
interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error("[VisionGuard ErrorBoundary]", error, info.componentStack);
  }

  reset = () => this.setState({ hasError: false, message: "" });

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4 text-center p-8">
            <div className="w-12 h-12 rounded-full bg-danger-subtle border border-danger-muted flex items-center justify-center text-danger text-2xl font-bold">
              !
            </div>
            <div>
              <h2 className="text-base font-semibold text-text-primary mb-1">
                Something went wrong
              </h2>
              <p className="text-sm text-text-secondary font-mono max-w-md break-all">
                {this.state.message}
              </p>
            </div>
            <button
              onClick={this.reset}
              className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors"
            >
              Try again
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
