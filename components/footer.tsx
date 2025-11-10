export function Footer() {
  return (
    <footer className="border-t border-border/60 bg-muted/30 mt-20">
      <div className="container px-6 py-8">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-muted-foreground">
          <p>© 2025 Zapier Triggers API</p>
          <a
            href="https://github.com/zapier/triggers-api"
            className="hover:text-foreground transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            Documentation
          </a>
        </div>
      </div>
    </footer>
  )
}
