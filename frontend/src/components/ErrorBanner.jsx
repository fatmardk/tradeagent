export default function ErrorBanner({ error }) {
  if (!error) return null;
  return (
    <div className="error-box">
      <strong>{error.code || 'Error'}:</strong> {error.message}
    </div>
  );
}
