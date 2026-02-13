import json
from playwright.sync_api import sync_playwright


URL = "https://ourworldindata.org/grapher/population-growth-rates"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")

        data = page.evaluate(
            """() => {
                const scripts = Array.from(document.scripts).map((s) => s.src || "[inline]");
                const stylesheets = Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map((l) => l.href);
                const modulePreloads = Array.from(document.querySelectorAll('link[rel="modulepreload"]')).map((l) => l.href);
                const inlineStyleTags = document.querySelectorAll('style').length;
                const svgCount = document.querySelectorAll('svg').length;
                const canvasCount = document.querySelectorAll('canvas').length;
                const grapherSelectors = [
                    '.GrapherComponent',
                    '#grapher',
                    '.GrapherHeader',
                    '.GrapherFooter',
                    '.ChartHeader',
                    '.charts',
                ];
                const grapherMatches = grapherSelectors.map((sel) => ({
                    selector: sel,
                    count: document.querySelectorAll(sel).length,
                }));
                const frameworkHints = {
                    reactData: Boolean(document.querySelector('[data-reactroot], [data-reactid]')),
                    nextJs: Boolean(document.querySelector('script[src*="_next"]')),
                    webpackChunks: scripts.some((src) => /chunk|webpack|bundle/i.test(src)),
                };
                const globals = {
                    Grapher: typeof window.Grapher !== 'undefined',
                    OWID: typeof window.OWID !== 'undefined',
                    d3: typeof window.d3 !== 'undefined',
                    Highcharts: typeof window.Highcharts !== 'undefined',
                    Plotly: typeof window.Plotly !== 'undefined',
                    React: typeof window.React !== 'undefined',
                    Vega: typeof window.vega !== 'undefined',
                    VegaEmbed: typeof window.vegaEmbed !== 'undefined',
                };
                const metaGenerator = document.querySelector('meta[name="generator"]')?.content || null;
                return {
                    title: document.title,
                    scripts,
                    stylesheets,
                    modulePreloads,
                    inlineStyleTags,
                    svgCount,
                    canvasCount,
                    grapherMatches,
                    frameworkHints,
                    globals,
                    metaGenerator,
                    userAgent: navigator.userAgent,
                };
            }"""
        )

        print(json.dumps(data, indent=2, sort_keys=True))
        browser.close()


if __name__ == "__main__":
    main()
