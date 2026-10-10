import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * A headless scheduling demonstration using the actual Java ActionListener API.
 * The Actor and Reviewer are simulations; no model or network is used.
 * Compile: javac --release 11 -d outputs/java examples/java/AgentActionListenerDemo.java
 * Run:     java -cp outputs/java AgentActionListenerDemo
 */
public final class AgentActionListenerDemo implements AutoCloseable {
    private static final String QUESTION_SUBMITTED = "question.submitted";
    private static final String ACTOR_COMPLETED = "actor.completed";
    private static final String REVIEWER_COMPLETED = "reviewer.completed";

    private final List<ActionListener> listeners = new CopyOnWriteArrayList<>();
    private final List<String> executionOrder = new CopyOnWriteArrayList<>();
    private final CompletableFuture<String> completion = new CompletableFuture<>();
    private final ExecutorService workers;
    private volatile String draft;

    public AgentActionListenerDemo() {
        AtomicInteger threadNumber = new AtomicInteger();
        workers = Executors.newFixedThreadPool(2, runnable ->
                new Thread(runnable, "agent-worker-" + threadNumber.incrementAndGet()));
        // The callback itself only submits work; the executor provides asynchrony.
        ActionListener schedulingListener = event -> workers.execute(() -> handle(event));
        listeners.add(schedulingListener);
    }

    private static void log(String message) {
        System.out.printf("[%s] %s%n", Thread.currentThread().getName(), message);
    }

    private void fire(String command) {
        log("emit " + command + "; listener callback runs synchronously here");
        ActionEvent event = new ActionEvent(this, ActionEvent.ACTION_PERFORMED, command);
        for (ActionListener listener : listeners) {
            listener.actionPerformed(event);
        }
    }

    private void handle(ActionEvent event) {
        try {
            switch (event.getActionCommand()) {
                case QUESTION_SUBMITTED:
                    executionOrder.add("Actor");
                    log("Actor.run: simulate reading a document and drafting an answer");
                    draft = "The fictional pilot lasts four weeks.";
                    fire(ACTOR_COMPLETED);
                    break;
                case ACTOR_COMPLETED:
                    if (draft == null) {
                        throw new IllegalStateException("Reviewer cannot run before the draft exists");
                    }
                    executionOrder.add("Reviewer");
                    log("Reviewer.run: simulate checking the draft against source evidence");
                    fire(REVIEWER_COMPLETED);
                    break;
                case REVIEWER_COMPLETED:
                    executionOrder.add("Completed");
                    completion.complete(draft);
                    break;
                default:
                    throw new IllegalArgumentException("Unknown event command");
            }
        } catch (Throwable failure) {
            completion.completeExceptionally(failure);
        }
    }

    public String run() throws Exception {
        log("Simulation only: no UI window, model call, or network request");
        fire(QUESTION_SUBMITTED);
        String result = completion.get(10, TimeUnit.SECONDS);
        if (!executionOrder.equals(List.of("Actor", "Reviewer", "Completed"))) {
            throw new IllegalStateException("Unexpected execution order: " + executionOrder);
        }
        log("verified execution order: " + String.join(" -> ", executionOrder));
        return result;
    }

    @Override
    public void close() throws InterruptedException {
        workers.shutdown();
        if (!workers.awaitTermination(5, TimeUnit.SECONDS)) {
            workers.shutdownNow();
            if (!workers.awaitTermination(5, TimeUnit.SECONDS)) {
                throw new IllegalStateException("Background workers failed to stop");
            }
        }
        log("executor terminated; safe exit");
    }

    public static void main(String[] args) throws Exception {
        try (AgentActionListenerDemo demo = new AgentActionListenerDemo()) {
            log("result: " + demo.run());
        }
    }
}
