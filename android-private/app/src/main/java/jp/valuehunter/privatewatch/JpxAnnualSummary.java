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
import java.util.List;
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

    record Annual(LocalDate end, LocalDate released, BigDecimal eps, BigDecimal bps, String source,
                  List<JpxShareRights.Adjustment> adjustments, String reportingBasis,
                  OperatingFacts operating) {
        Annual(LocalDate end, LocalDate released, BigDecimal eps, BigDecimal bps, String source,
               List<JpxShareRights.Adjustment> adjustments, String reportingBasis) {
            this(end, released, eps, bps, source, adjustments, reportingBasis, null);
        }
        Annual(LocalDate end, LocalDate released, BigDecimal eps, BigDecimal bps, String source) {
            this(end, released, eps, bps, source, List.of(), "");
        }

        Annual(LocalDate end, LocalDate released, BigDecimal eps, BigDecimal bps, String source,
               List<JpxShareRights.Adjustment> adjustments) {
            this(end, released, eps, bps, source, adjustments, "");
        }

        boolean usable(LocalDate day) {
            return released.isBefore(day) && !end.isBefore(day.minusMonths(16));
        }

        ValueCandidateScreen.Level level(LocalDate day, BigDecimal close) {
            return usable(day) ? ValueCandidateScreen.assess(
                    onShareBasis(day, close, true), onShareBasis(day, eps, false), onShareBasis(day, bps, false))
                    : ValueCandidateScreen.Level.HELD;
        }

        BigDecimal onShareBasis(LocalDate day, BigDecimal value, boolean price) {
            if (value == null) return null;
            for (var event : adjustments) {
                if (!event.exDay().isAfter(day)) value = value.multiply(price ? event.newShares() : event.oldShares());
            }
            return value;
        }
    }

    record OperatingFacts(BigDecimal cashFlow, BigDecimal revenue, BigDecimal assets, BigDecimal netAssets,
                          BigDecimal issuedShares, BigDecimal operatingProfit, BigDecimal priorProfit,
                          BigDecimal priorCashFlow) {}

    private JpxAnnualSummary() {}

    static Annual read(String body, String code, LocalDate released, String source, boolean corrected) {
        if (body.startsWith("\ufeff")) body = body.substring(1);
        if (FORBIDDEN_XML.matcher(body).find()) return null;
        try {
            var factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            // Android's DOM factory does not implement the Xerces feature URIs.
            // Reject declarations before DOM parsing and refuse any external resolution.
            var builder = factory.newDocumentBuilder();
            builder.setEntityResolver((publicName, systemName) -> {
                throw new org.xml.sax.SAXException("External XML identifiers are not allowed");
            });
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
            // Only an absent BPS fact is optional. Conflicting or invalid supplied facts remain rejected.
            BigDecimal bps = null;
            var candidates = root.getElementsByTagNameNS(IX, "nonFraction");
            for (int i=0;i<candidates.getLength();i++) {
                var candidate=(Element)candidates.item(i);
                if (instant.equals(candidate.getAttribute("contextRef"))
                        && ("tse-ed-t:"+bpsTag).equals(candidate.getAttribute("name"))) {
                    bps=number(root,bpsTag,instant);
                    break;
                }
            }
            var operating = "NetIncomePerShare".equals(epsTag)
                    ? operatingFacts(root, code, member, duration, instant, start, end) : null;
            return new Annual(end, released, eps, bps, source, List.of(), member + "/" + epsTag, operating);
        } catch (Exception invalid) {
            // A changed taxonomy, incomplete filing or ambiguous financials cannot enter the screen.
            return null;
        }
    }

    private static OperatingFacts operatingFacts(Element root, String code, String member,
                                                 String duration, String instant, LocalDate start, LocalDate end) {
        try {
            String shareContext = "CurrentYearInstant_NonConsolidatedMember_ResultMember";
            var shares = context(root, shareContext, code, "NonConsolidatedMember");
            if (!end.equals(LocalDate.parse(only(shares, XBRL, "instant")))) return null;
            var issued = amount(root, "NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock",
                    shareContext, "xbrli:shares", true);
            var revenue = amount(root, "NetSales", duration, "iso4217:JPY", false);
            var cash = amountIfPresent(root, "CashFlowsFromOperatingActivities", duration);
            var assets = amount(root, "TotalAssets", instant, "iso4217:JPY", false);
            var netAssets = amount(root, "NetAssets", instant, "iso4217:JPY", false);
            if (issued.signum() <= 0 || revenue.signum() <= 0 || assets.signum() <= 0
                    || netAssets.compareTo(assets) > 0) return null;
            var profit = optionalAmount(root, "OperatingIncome", duration);
            String priorId = "PriorYearDuration_" + member + "_ResultMember";
            BigDecimal prior = null;
            BigDecimal priorCash = null;
            try {
                var period = context(root, priorId, code, member);
                var priorStart = LocalDate.parse(only(period, XBRL, "startDate"));
                var priorEnd = LocalDate.parse(only(period, XBRL, "endDate"));
                long days = ChronoUnit.DAYS.between(priorStart, priorEnd) + 1;
                if (priorEnd.plusDays(1).equals(start) && days >= 350 && days <= 380) {
                    prior = optionalAmount(root, "OperatingIncome", priorId);
                    priorCash = optionalAmount(root, "CashFlowsFromOperatingActivities", priorId);
                }
            } catch (IllegalArgumentException | java.time.DateTimeException missingPrior) {
                // Without a comparable prior year the highest tier stays unavailable.
            }
            return new OperatingFacts(cash, revenue, assets, netAssets, issued, profit, prior, priorCash);
        } catch (IllegalArgumentException | java.time.DateTimeException invalid) {
            return null;
        }
    }

    private static BigDecimal amountIfPresent(Element root, String name, String context) {
        var facts = root.getElementsByTagNameNS(IX, "nonFraction");
        for (int i = 0; i < facts.getLength(); i++) {
            var item = (Element) facts.item(i);
            if (context.equals(item.getAttribute("contextRef"))
                    && ("tse-ed-t:" + name).equals(item.getAttribute("name"))) {
                return amount(root, name, context, "iso4217:JPY", false);
            }
        }
        return null;
    }

    private static BigDecimal optionalAmount(Element root, String name, String context) {
        try {
            return amount(root, name, context, "iso4217:JPY", false);
        } catch (IllegalArgumentException unavailable) {
            return null;
        }
    }

    private static BigDecimal amount(Element root, String name, String context, String measure, boolean shares) {
        var item = fact(root, "nonFraction", name, context);
        String unitRef = item.getAttribute("unitRef");
        var units = root.getElementsByTagNameNS(XBRL, "unit");
        Element found = null;
        for (int i = 0; i < units.getLength(); i++) {
            var unit = (Element) units.item(i);
            if (!unitRef.equals(unit.getAttribute("id"))) continue;
            if (found != null) throw new IllegalArgumentException("Ambiguous unit");
            found = unit;
        }
        String scale = item.getAttribute("scale");
        if (unitRef.isEmpty() || found == null || !measure.equals(only(found, XBRL, "measure"))
                || found.getElementsByTagNameNS(XBRL, "divide").getLength() != 0
                || !"0".equals(scale) && (shares || !"3".equals(scale) && !"6".equals(scale))
                || "true".equals(item.getAttributeNS("http://www.w3.org/2001/XMLSchema-instance", "nil"))) {
            throw new IllegalArgumentException("Invalid operating fact unit");
        }
        String magnitude = normalized(item.getTextContent());
        String sign = item.getAttribute("sign");
        if (!NUMBER.matcher(magnitude).matches() || magnitude.length() > 24
                || !sign.isEmpty() && !sign.equals("-") || shares && magnitude.contains(".")) {
            throw new IllegalArgumentException("Invalid operating fact number");
        }
        return new BigDecimal(sign + magnitude.replace(",", "")).scaleByPowerOfTen(Integer.parseInt(scale));
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
