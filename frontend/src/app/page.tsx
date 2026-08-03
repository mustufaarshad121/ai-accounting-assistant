import BackendStatus from "@/components/BackendStatus";

/**
 * Scaffold landing page.
 *
 * Minimal, professional placeholder for the AI-Powered Accounting Assistant.
 * Shows the project title, a short description, the current build phase, and
 * live backend connectivity. No accounting screens, auth, or mock financial
 * data — those arrive in later feature branches.
 */
export default function Home() {
  return (
    <main className="flex-1 flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-2xl text-center">
        <span className="inline-block rounded-full border border-black/10 dark:border-white/15 px-3 py-1 text-xs font-medium uppercase tracking-wide text-black/60 dark:text-white/60">
          Current phase: Project Scaffold
        </span>

        <h1 className="mt-6 text-3xl sm:text-4xl font-semibold tracking-tight">
          AI-Powered Accounting Assistant
        </h1>

        <p className="mt-4 text-base sm:text-lg text-black/70 dark:text-white/70">
          A full-stack, double-entry accounting application with an integrated
          AI assistant. This is the scaffold foundation — the frontend, backend
          health endpoint, and container setup are in place. Accounting
          features and the AI agent are implemented in upcoming branches.
        </p>

        <div className="mt-8 flex justify-center">
          <BackendStatus />
        </div>

        <p className="mt-10 text-xs text-black/40 dark:text-white/40">
          Next.js · TypeScript · Tailwind CSS — talking to FastAPI over
          NEXT_PUBLIC_API_URL
        </p>
      </div>
    </main>
  );
}
