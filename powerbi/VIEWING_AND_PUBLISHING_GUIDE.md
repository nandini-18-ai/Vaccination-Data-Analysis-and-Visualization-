# Power BI Dashboard: Viewing and Publishing

## View locally

Open `Vaccination_Data_Analysis.pbix` with **Power BI Desktop**.

## Share the dashboard publicly

A `.pbix` file stored on GitHub cannot be displayed as an interactive dashboard directly in a browser. To let others view the interactive report:

1. Open the `.pbix` file in Power BI Desktop.
2. Sign in to Power BI Service.
3. Select **Publish** and choose a workspace.
4. In Power BI Service, use **File → Embed report → Publish to web (public)** if your institution permits public sharing.
5. Copy the generated public report URL and add it to the project README and EDA notebook.

## Important privacy warning

**Publish to web makes the report and its underlying report data publicly accessible.** Use this option only after confirming that the report contains no personal, confidential, restricted, or institution-owned information and that public publication is allowed. If public publication is not allowed, share the report only through an appropriately restricted Power BI workspace.

## Repository contents

- `Vaccination_Data_Analysis.pbix`: the interactive Power BI report file.
- `DAX_MEASURES.md`: DAX measures used or documented for the report.
- `REPORT_SPECIFICATION.md`: report pages, visuals, and analytical notes.
- `BUILD_CHECKLIST.md`: Power BI construction and validation checklist.
