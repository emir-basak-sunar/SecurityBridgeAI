/** Backend API base URL. Aynı makineden veya ağdaki PC'den erişim için hostname kullanır. */
export function getApiBase(): string {
    if (import.meta.env.VITE_API_BASE_URL) {
        return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, "");
    }
    const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
    return `http://${host}:8000`;
}
