package jp.valuehunter.privatewatch;

import org.w3c.dom.Element;
import org.xml.sax.InputSource;

import javax.xml.parsers.DocumentBuilderFactory;
import java.io.StringReader;
import java.math.BigDecimal;
import java.text.Normalizer;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.time.chrono.JapaneseChronology;
import java.time.chrono.JapaneseEra;
import java.util.regex.Pattern;

/** Actual full-year EPS and book value per share from a JPX Inline XBRL summary. */
final class JpxAnnualSummary {
    private static final String XBRL = "http://www.xbrl.org/2003/instance";
    private static final String DIMENSIONS = "http://xbrl.org/2006/xbrldi";
    private static final String IX = "http://www.xbrl.org/2008/inlineXBRL";
    private static final Pattern DATE = Pattern.compile("(\\d{4})年(\\d{1,2})月(\\d{1,2})日");
    private static final Pattern ERA_DATE = Pattern.compile("(令和|平成)(元|[0-9]{1,2})年([0-9]{1,2})月([0-9]{1,2})日");
    private static final Pattern NUMBER = Pattern.compile("(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\\.[0-9]+)?");
    private static final Pattern FORBIDDEN_XML = Pattern.compile("<!\\s*(?:DOCTYPE|ENTITY)", Pattern.CASE_INSENSITIVE);

    record Annual(LocalDate end, LocalDate released, BigDecimal eps, BigDecimal bps, String source) {
        boolean usable(LocalDate day) {
            return released.isBefore(day) && !end.isBefore(day.minusMonths(16));
        }

        ValueCandidateScreen.Level level(LocalDate day, BigDecimal close) {
            return usable(day) ? ValueCandidateScreen.assess(close, eps, bps) : ValueCandidateScreen.Level.HELD;
        }
    }

    private JpxAnnualSummary() {}

    static Annual read(String body, String code, LocalDate released, String source, boolean corrected) {
        if (body.startsWith("\ufeff")) body = body.substring(1);
        if (FORBIDDEN_XML.matcher(body).find()) return null;
        try {
            var factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setExpandEntityReferences(false);
            factory.setXIncludeAware(false);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
            var builder = factory.newDocumentBuilder();
            builder.setEntityResolver((publicName, systemName) -> new InputSource(new StringReader("")));
            var root = builder.parse(new InputSource(new StringReader(body))).getDocumentElement();
            String issuer = uniqueFact(root, "nonNumeric", "SecuritiesCode", "CurrentYearInstant");
            if (!issuer.equals(code) && !issuer.equals(code + "0")) return null;
            String title = uniqueFact(root, "nonNumeric", "DocumentName", "CurrentYearInstant");
            LocalDate coverDate = documentDate(uniqueFact(root, "nonNumeric", "FilingDate", "CurrentYearInstant"));
            if (!title.contains("決算短信") || title.matches(".*(?:四半期|中間|半期).*")
                    || coverDate == null || coverDate.isAfter(released)
                    || !corrected && !coverDate.equals(released)) return null;
            boolean standalone = title.contains("(非連結)");
            if (!standalone && !title.contains("(連結)")) return null;
            String member = standalone ? "NonConsolidatedMember" : "ConsolidatedMember";
            String duration = "CurrentYearDuration_" + member + "_ResultMember";
            String instant = "CurrentYearInstant_" + member + "_ResultMember";
            var earningsContext = context(root, duration, code, member);
            var equityContext = context(root, instant, code, member);
            LocalDate start = LocalDate.parse(only(earningsContext, XBRL, "startDate"));
            LocalDate end = LocalDate.parse(only(earningsContext, XBRL, "endDate"));
            long days = ChronoUnit.DAYS.between(start, end) + 1;
            if (days < 350 || days > 380 || !end.equals(LocalDate.parse(only(equityContext, XBRL, "instant")))
                    || end.isAfter(coverDate)) return null;

            String epsTag = "NetIncomePerShare";
            String bpsTag = "NetAssetsPerShare";
            if (title.contains("IFRS")) {
                epsTag = "BasicEarningsPerShareIFRS";
                bpsTag = "EquityAttributableToOwnersOfParentPerShareIFRS";
            } else if (title.contains("米国基準")) {
                epsTag = "NetIncomePerShareUS";
                bpsTag = "ShareholdersEquityPerShareUS";
            } else if (!title.contains("日本基準")) {
                return null;
            }
            var eps = number(root, epsTag, duration);
            var bps = number(root, bpsTag, instant);
            return new Annual(end, released, eps, bps, source);
        } catch (Exception invalid) {
            // A changed taxonomy, incomplete filing or ambiguous financials cannot enter the screen.
            return null;
        }
    }

    static LocalDate documentDate(String value) {
        var western = DATE.matcher(value);
        if (western.matches()) return LocalDate.of(Integer.parseInt(western.group(1)),
                Integer.parseInt(western.group(2)), Integer.parseInt(western.group(3)));
        var era = ERA_DATE.matcher(value);
        if (!era.matches()) return null;
        var calendar = "令和".equals(era.group(1)) ? JapaneseEra.REIWA : JapaneseEra.HEISEI;
        int year = "元".equals(era.group(2)) ? 1 : Integer.parseInt(era.group(2));
        return LocalDate.from(JapaneseChronology.INSTANCE.date(calendar, year,
                Integer.parseInt(era.group(3)), Integer.parseInt(era.group(4))));
    }

    private static Element context(Element root, String id, String code, String member) {
        var elements = root.getElementsByTagNameNS(XBRL, "context");
        Element found = null;
        for (int i = 0; i < elements.getLength(); i++) {
            var element = (Element) elements.item(i);
            if (!id.equals(element.getAttribute("id"))) continue;
            if (found != null) throw new IllegalArgumentException("Duplicate period context");
            found = element;
        }
        if (found == null || !only(found, XBRL, "identifier").equals(code + "0")) {
            throw new IllegalArgumentException("Incorrect period issuer");
        }
        var dimensions = found.getElementsByTagNameNS(DIMENSIONS, "explicitMember");
        boolean results = false;
        boolean scope = false;
        for (int i = 0; i < dimensions.getLength(); i++) {
            var dimension = (Element) dimensions.item(i);
            String axis = dimension.getAttribute("dimension");
            String value = dimension.getTextContent().strip();
            if (axis.endsWith(":ResultForecastAxis") && value.endsWith(":ResultMember")) results = true;
            else if (axis.endsWith(":ConsolidatedNonconsolidatedAxis") && value.endsWith(":" + member)) scope = true;
            else throw new IllegalArgumentException("Unrecognized period dimension");
        }
        if (!scope || !results || dimensions.getLength() != 2) throw new IllegalArgumentException("Incorrect scope");
        return found;
    }

    private static BigDecimal number(Element root, String name, String context) {
        var fact = fact(root, "nonFraction", name, context);
        if (!"JPYPerShares".equals(fact.getAttribute("unitRef"))
                || !"0".equals(fact.getAttribute("scale"))
                || "true".equals(fact.getAttributeNS("http://www.w3.org/2001/XMLSchema-instance", "nil"))) {
            throw new IllegalArgumentException("Invalid per-share amount");
        }
        var units = root.getElementsByTagNameNS(XBRL, "unit");
        Element unit = null;
        for (int i = 0; i < units.getLength(); i++) {
            var candidate = (Element) units.item(i);
            if (!"JPYPerShares".equals(candidate.getAttribute("id"))) continue;
            if (unit != null) throw new IllegalArgumentException("Duplicate unit");
            unit = candidate;
        }
        if (unit == null || !"iso4217:JPY".equals(only(unit, XBRL, "unitNumerator"))
                || !"xbrli:shares".equals(only(unit, XBRL, "unitDenominator"))) {
            throw new IllegalArgumentException("Invalid currency or unit");
        }
        String magnitude = normalized(fact.getTextContent());
        String sign = fact.getAttribute("sign");
        if (!NUMBER.matcher(magnitude).matches() || !sign.isEmpty() && !sign.equals("-")) {
            throw new IllegalArgumentException("Invalid numeric format");
        }
        return new BigDecimal(sign + magnitude.replace(",", ""));
    }

    private static String uniqueFact(Element root, String type, String name, String context) {
        return normalized(fact(root, type, name, context).getTextContent());
    }

    private static Element fact(Element root, String type, String name, String context) {
        var facts = root.getElementsByTagNameNS(IX, type);
        Element found = null;
        for (int i = 0; i < facts.getLength(); i++) {
            var candidate = (Element) facts.item(i);
            if (!context.equals(candidate.getAttribute("contextRef"))
                    || !("tse-ed-t:" + name).equals(candidate.getAttribute("name"))) continue;
            if (found != null) throw new IllegalArgumentException("Ambiguous fact");
            found = candidate;
        }
        if (found == null) throw new IllegalArgumentException("Fact missing");
        return found;
    }

    private static String only(Element root, String namespace, String tag) {
        var elements = root.getElementsByTagNameNS(namespace, tag);
        if (elements.getLength() != 1) throw new IllegalArgumentException("Missing or ambiguous " + tag);
        return elements.item(0).getTextContent().strip();
    }

    static String normalized(String text) {
        return Normalizer.normalize(text, Normalizer.Form.NFKC).replaceAll("\\s+", "");
    }
}
