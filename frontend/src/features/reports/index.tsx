import { useState } from "react";
import { useScanwickChrome } from "@/features/landing/chrome";
import { IntelligenceSidebar } from "@/features/intelligence/components/sidebar";
import { IntelligenceTopbar } from "@/features/intelligence/components/topbar";
import { ReportLibraryPage } from "./pages/report-library";
import { ScheduledReportsPage } from "./pages/scheduled-reports";
import { ExportHistoryPage } from "./pages/export-history";
import { sectionGroups, type ReportsSectionId } from "./sections";

export default function Reports() {
  const { theme, toggleTheme } = useScanwickChrome();
  const [activeSection, setActiveSection] = useState<ReportsSectionId>("report-library");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <main className={`scanwick-page fi-shell ${theme === "light" ? "theme-light" : ""}`}>
      <IntelligenceTopbar
        theme={theme}
        onToggleTheme={toggleTheme}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        dateRangeLabel="25 Mar – 17 Jun"
        moduleLabel="Report Library"
      />
      <div className="fi-body">
        <IntelligenceSidebar
          title="Reports"
          groups={sectionGroups.map((group) => ({ items: [...group.items] }))}
          open={sidebarOpen}
          activeSection={activeSection}
          onSelect={(id) => setActiveSection(id as ReportsSectionId)}
        />
        <div className="fi-content">
          <div className="fi-content-inner">
            {activeSection === "report-library" ? <ReportLibraryPage /> : null}
            {activeSection === "scheduled-reports" ? <ScheduledReportsPage /> : null}
            {activeSection === "export-history" ? <ExportHistoryPage /> : null}
          </div>
        </div>
      </div>
    </main>
  );
}
