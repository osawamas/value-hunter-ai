package jp.valuehunter.privatewatch;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

public class NotificationHistoryTest {
    private static final long DAY = TimeUnit.DAYS.toMillis(1);
    private static final long NOW = 10 * DAY;
    private static final Runnable UNEXPECTED = () -> fail("Unexpected notification or screen wake");
    @Rule public TemporaryFolder directory = new TemporaryFolder();

    private File history() {
        return new File(directory.getRoot(), "history.json");
    }

    @Test public void submitsImmediatelyAndRestartDoesNotRepeatOrWake() throws Exception {
        var posts = new AtomicInteger();
        var wakes = new AtomicInteger();
        assertTrue(NotificationHistory.deliver(history(), "5-foo", "東証候補", "1001 · PER条件入り",
                NOW, () -> 0, posts::incrementAndGet, wakes::incrementAndGet));
        assertTrue(NotificationHistory.deliver(history(), "5-foo", "東証候補", "1001 · PER条件入り",
                NOW + 1000, () -> 0, UNEXPECTED, UNEXPECTED));
        assertEquals(1, posts.get());
        assertEquals(1, wakes.get());
        assertEquals(List.of(new NotificationHistory.Entry("5-foo", NOW, "東証候補", "1001 · PER条件入り")),
                NotificationHistory.recent(history(), NOW + 1000));
    }

    @Test public void recoversActiveOrDismissedNotificationAfterInterruption() throws Exception {
        var file = history();
        assertTrue(NotificationHistory.deliver(file, "5-foo", "東証候補", "1001", NOW,
                () -> NOW - 10000, UNEXPECTED, UNEXPECTED));
        assertTrue(NotificationHistory.deliver(file, "8-foo", "米国株候補", "ABC", NOW,
                () -> NOW - 1000, UNEXPECTED, UNEXPECTED));
        var entries = NotificationHistory.recent(file, NOW);
        assertEquals(List.of("8-foo", "5-foo"), entries.stream().map(NotificationHistory.Entry::receipt).toList());
        assertEquals(NOW - 10000, entries.get(1).postedAt());
    }

    @Test public void rejectedSubmissionDoesNotSaveOrWakeAndCanRetry() throws Exception {
        var file = history();
        assertThrows(SecurityException.class, () -> NotificationHistory.deliver(file, "5-foo", "東証候補", "1001", NOW,
                () -> 0, () -> { throw new SecurityException(); }, UNEXPECTED));
        assertTrue(NotificationHistory.recent(file, NOW).isEmpty());
        assertTrue(NotificationHistory.deliver(file, "5-foo", "東証候補", "1001", NOW,
                () -> 0, () -> {}, () -> {}));
        assertEquals(1, NotificationHistory.recent(file, NOW).size());
    }

    @Test public void prunesExpiredEntriesAndKeepsTheOriginalWhenTheClockMovesBack() throws Exception {
        var file = history();
        NotificationHistory.deliver(file, "expired", "古い通知", "E", NOW - 7 * DAY, () -> 0, () -> {}, () -> {});
        NotificationHistory.deliver(file, "recent", "新しい通知", "R", NOW, () -> 0, () -> {}, () -> {});
        assertEquals(List.of("recent"), NotificationHistory.recent(file, NOW - 100)
                .stream().map(NotificationHistory.Entry::receipt).toList());
        assertEquals(List.of("recent"), NotificationHistory.recent(file, NOW)
                .stream().map(NotificationHistory.Entry::receipt).toList());
        assertTrue(NotificationHistory.recent(file, NOW + 7 * DAY).isEmpty());
    }

    @Test public void concurrentWorkersShareTheSameReceipt() throws Exception {
        var file = history();
        var posts = new AtomicInteger();
        var start = new CountDownLatch(1);
        var threads = Executors.newFixedThreadPool(2);
        try {
            java.util.concurrent.Callable<Boolean> notify = () -> {
                start.await();
                return NotificationHistory.deliver(file, "5-foo", "東証候補", "1001", NOW,
                        () -> 0, posts::incrementAndGet, () -> {});
            };
            var a = threads.submit(notify);
            var b = threads.submit(notify);
            start.countDown();
            assertTrue(a.get(5, TimeUnit.SECONDS));
            assertTrue(b.get(5, TimeUnit.SECONDS));
            assertEquals(1, posts.get());
        } finally {
            threads.shutdownNow();
        }
    }

    @Test public void keepsAllSymbolsEvenWithACappedPreview() throws Exception {
        String full = "終値の確認\n" + "1301 · 条件入り\n".repeat(12) + "9999 · 条件入り";
        String another = full.replace("9999", "9998");
        assertEquals(ScanWorker.notificationPreview(full), ScanWorker.notificationPreview(another));
        assertNotEquals(ScanWorker.notificationReceipt("条件入り", full),
                ScanWorker.notificationReceipt("条件入り", another));
        assertFalse(ScanWorker.notificationPreview(full).contains("9999"));
        NotificationHistory.deliver(history(), "full", "条件入り", full, NOW, () -> 0, () -> {}, () -> {});
        assertTrue(NotificationHistory.recent(history(), NOW).get(0).detail().contains("9999"));
    }

    @Test public void afterAFailedHistoryWriteTheSystemReceiptPreventsAnotherPost() throws Exception {
        var file = history();
        assertThrows(IOException.class, () -> NotificationHistory.deliver(file, "5-foo", "候補", "1001", NOW,
                () -> 0, () -> assertTrue(file.mkdir()), () -> {}));
        assertTrue(file.delete());
        assertTrue(NotificationHistory.deliver(file, "5-foo", "候補", "1001", NOW + 1000,
                () -> NOW, UNEXPECTED, UNEXPECTED));
        assertEquals(NOW, NotificationHistory.recent(file, NOW + 1000).get(0).postedAt());
    }

    @Test public void aCorruptRecordDoesNotHideOtherNotifications() throws Exception {
        var file = history();
        Files.write(file.toPath(), """
                [{"receipt":"old","at":-5,"title":"古い"},false,
                 {"receipt":"good","at":864000000,"title":"有効","detail":"1234"}]
                """.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        assertEquals(List.of("good"), NotificationHistory.recent(file, NOW)
                .stream().map(NotificationHistory.Entry::receipt).toList());
        assertThrows(IOException.class, () -> NotificationHistory.recent(directory.getRoot(), NOW));
    }
    @Test public void wakeFailureAfterSuccessfulPostStillPersistsReceipt() throws Exception {
        var file = history();
        var posts = new AtomicInteger();
        assertTrue(NotificationHistory.deliver(file, "5-wake", "東証候補", "1001", NOW,
                () -> 0, posts::incrementAndGet, () -> { throw new IllegalStateException("wake denied"); }));
        assertEquals(1, posts.get());
        assertEquals(1, NotificationHistory.recent(file, NOW).size());
        assertTrue(NotificationHistory.deliver(file, "5-wake", "東証候補", "1001", NOW + 1000,
                () -> 0, UNEXPECTED, UNEXPECTED));
        assertEquals(1, posts.get());
    }

    @Test public void unsortedLegacyHistoryKeepsNewestBeyondFirst256Rows() throws Exception {
        var file = history();
        var rows = new org.json.JSONArray();
        for (int i = 0; i < 300; i++) {
            rows.put(new org.json.JSONObject().put("receipt", "old-" + i)
                    .put("at", NOW - 300_000 + i * 1000L)
                    .put("title", "候補" + i).put("detail", "過去の通知"));
        }
        Files.write(file.toPath(), rows.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
        var recent = NotificationHistory.recent(file, NOW);
        assertEquals(256, recent.size());
        assertEquals("old-299", recent.get(0).receipt());
        assertEquals("old-44", recent.get(255).receipt());
        assertFalse(recent.stream().anyMatch(row -> row.receipt().equals("old-0")));
        assertTrue(NotificationHistory.deliver(file, "old-299", "候補299", "過去の通知",
                NOW + 1000, () -> 0, UNEXPECTED, UNEXPECTED));
    }

    @Test public void duplicateLegacyReceiptsKeepNewestTimestampRegardlessOfRowOrder() throws Exception {
        var file = history();
        Files.write(file.toPath(), ("[{\"receipt\":\"same\",\"at\":" + (NOW - 5000)
                + ",\"title\":\"古い\"},{\"receipt\":\"same\",\"at\":" + (NOW - 1000)
                + ",\"title\":\"新しい\"}]").getBytes(java.nio.charset.StandardCharsets.UTF_8));
        var entries = NotificationHistory.recent(file, NOW);
        assertEquals(1, entries.size());
        assertEquals(NOW - 1000, entries.get(0).postedAt());
        assertEquals("新しい", entries.get(0).title());
    }
    @Test public void fullHistoryRetainsNewReceiptWhenClockMovesBackwards() throws Exception {
        var file = history();
        var rows = new org.json.JSONArray();
        for (int i = 0; i < 256; i++) {
            rows.put(new org.json.JSONObject().put("receipt", "old-" + i)
                    .put("at", NOW - 256 + i)
                    .put("title", "既存").put("detail", "保存済み"));
        }
        Files.write(file.toPath(), rows.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
        var posts = new AtomicInteger();
        assertTrue(NotificationHistory.deliver(file, "new-clock-rollback", "新候補", "1001",
                NOW - 1000, () -> 0, posts::incrementAndGet, () -> {}));
        var saved = NotificationHistory.recent(file, NOW);
        assertEquals(256, saved.size());
        assertTrue(saved.stream().anyMatch(entry -> entry.receipt().equals("new-clock-rollback")));
        assertFalse(saved.stream().anyMatch(entry -> entry.receipt().equals("old-0")));
        assertTrue(NotificationHistory.deliver(file, "new-clock-rollback", "新候補", "1001",
                NOW, () -> 0, UNEXPECTED, UNEXPECTED));
        assertEquals(1, posts.get());
    }

    @Test public void durableReceiptExistsBeforeOptionalWakeAndSurvivesWakeFailure() throws Exception {
        var file = history();
        var posts = new AtomicInteger();
        assertTrue(NotificationHistory.deliver(file, "wake-after-save", "候補", "1001", NOW,
                () -> 0, posts::incrementAndGet, () -> {
                    try {
                        assertEquals("wake-after-save", NotificationHistory.recent(file, NOW).get(0).receipt());
                    } catch (IOException e) {
                        throw new AssertionError(e);
                    }
                    throw new IllegalStateException("wake unavailable");
                }));
        assertEquals(1, posts.get());
        assertTrue(NotificationHistory.deliver(file, "wake-after-save", "候補", "1001", NOW + 1000,
                () -> 0, UNEXPECTED, UNEXPECTED));
        assertEquals(1, posts.get());
    }

}
