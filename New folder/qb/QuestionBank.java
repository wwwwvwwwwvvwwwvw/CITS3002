import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import java.util.concurrent.*;

enum MessageType {
    LOGIN,
    QUESTIONS,
    QUESTION_BANK,
    MARK,
    MARKED,
}

class LoginMessage {
    public String user;

    public LoginMessage(String user) {
        this.user = user;
    }

    public static LoginMessage fromJson(String json) {
        int start = json.indexOf("\"user\": \"") + 9;
        String user = json.substring(start, json.lastIndexOf("\""));
        return new LoginMessage(user);
    }
}

class QuestionsMessage {
    public String user;
    public List<Question> questions;

    public QuestionsMessage(String user, List<Question> questions) {
        this.user = user;
        this.questions = questions;
    }

    public String toJson() {
        StringBuilder questionsJson = new StringBuilder();
        questionsJson.append("{\"user\": \"");
        questionsJson.append(user);
        questionsJson.append("\", \"questions\": ");
        questionsJson.append("[");
        for (int i = 0; i < questions.size(); i++) {
            questionsJson.append(questions.get(i).toJson());
            if (i < questions.size() - 1) {
                questionsJson.append(",");
            }
        }
        questionsJson.append("]}");

        return questionsJson.toString();
    }
}

class Test {
    public List<String> parameters;
    public String output;

    public Test(List<String> parameters, String output) {
        this.parameters = parameters;
        this.output = output;
    }

    public static Test fromJson(String json) {
        String output = unescapeNewlines(getValue(json, "output"));
        List<String> parameters = getValues(json, "parameters");
        return new Test(parameters, output);
    }

    private static String getValue(String json, String key) {
        String keyWithQuotes = "\"" + key + "\": \"";
        int start = json.indexOf(keyWithQuotes) + keyWithQuotes.length();
        int end = json.indexOf("\"", start);
        return json.substring(start, end);
    }

    private static List<String> getValues(String json, String key) {
        String keyWithQuotes = "\"" + key + "\": [";
        int start = json.indexOf(keyWithQuotes) + keyWithQuotes.length();
        int end = json.indexOf("]", start);
        List<String> strings = new ArrayList<>();
        Pattern pattern = Pattern.compile("\"(.*?)\"");
        Matcher matcher = pattern.matcher(json.substring(start, end));
        while (matcher.find()) {
            String matchedString = matcher.group(1);
            strings.add(matchedString);
        }
        return strings;
    }

    private static String unescapeNewlines(String value) {
        return value.replaceAll("\\\\n", "\n").replaceAll("\\\\t", "\t");
    }
}

class Question {
    public String id;
    public String question;
    public String type;
    public String answer;
    public List<Test> tests;

    public Question(String id, String question, String type, String answer, List<Test> tests) {
        this.id = id;
        this.question = question;
        this.type = type;
        this.answer = answer;
        this.tests = tests;
    }

    public String toJson() {
        return "{\"id\":\"" + id + "\",\"question\":\"" + question + "\",\"type\":\"" + type + "\"}";
    }

    public static Question fromJson(String json) {
        System.out.println(json);
        String id = getValue(json, "id");
        String question = getValue(json, "question");
        String type = getValue(json, "type");
        String answer = getValue(json, "answer");
        List<Test> tests = getTestsFromJson(json);
        return new Question(id, question, type, answer, tests);
    }

    private static String getValue(String json, String key) {
        String keyWithQuotes = "\"" + key + "\": \"";
        int start = json.indexOf(keyWithQuotes) + keyWithQuotes.length();
        int end = json.indexOf("\"", start);
        return json.substring(start, end);
    }

    private static List<Test> getTestsFromJson(String json) {
        List<Test> tests = new ArrayList<>();
        int start = json.indexOf("\"tests\":") + "\"tests\": [".length();
        int end = json.lastIndexOf("]");
        if (start >= 0 && end >= 0) {
            String testsJson = json.substring(start, end);
            while (testsJson.contains("{")) {
                int testStart = testsJson.indexOf("{");
                int testEnd = testsJson.indexOf("}", testStart);
                if (testStart >= 0 && testEnd >= 0) {
                    String testJson = testsJson.substring(testStart, testEnd + 1);
                    Test test = Test.fromJson(testJson);
                    tests.add(test);
                    testsJson = testsJson.substring(testEnd + 1).trim();
                    if (testsJson.startsWith(",")) {
                        testsJson = testsJson.substring(1).trim();
                    }
                }
            }
        }
        return tests;
    }
}

class QuestionBankMessage {
    public String language;
    public int portUsed;

    public QuestionBankMessage(String language, int portUsed) {
        this.language = language;
        this.portUsed = portUsed;
    }

    public String toJson() {
        return "{\"language\":\"" + language + "\",\"port-used\":" + portUsed + "}";
    }

}

class MarkedMessage {
    public String id;
    public String user;
    public String answer;
    public boolean correct;
    public String correctAnswer;

    public MarkedMessage(String id, String user, String answer, boolean correct, String correctAnswer) {
        this.id = id;
        this.answer = answer;
        this.user = user;
        this.correct = correct;
        this.correctAnswer = correctAnswer;
    }

    public String toJson() {
        return "{\"id\":\"" + id + "\",\"user\":\"" + user + "\",\"answer\":\"" + answer + "\",\"correct\":"
                + String.valueOf(correct) + ",\"correct-answer\":\"" + correctAnswer + "\"}";
    }
}

class MarkMessage {
    public String id;
    public String type;
    public String answer;
    public String user;

    public MarkMessage(String id, String type, String answer, String user) {
        this.id = id;
        this.type = type;
        this.answer = answer;
        this.user = user;
    }

    public static MarkMessage fromJson(String json) {
        String id = getValue(json, "id");
        String type = getValue(json, "type");
        String answer = getValue(json, "answer");
        String user = getValue(json, "user");
        return new MarkMessage(id, type, answer, user);
    }

    private static String getValue(String json, String key) {
        int start = json.indexOf("\"" + key + "\": \"") + key.length() + 5;
        int end = json.indexOf("\"", start);
        return json.substring(start, end);
    }
}

class Message {
    public MessageType type;
    public String message;

    public Message(MessageType type, String message) {
        this.type = type;
        this.message = message;
    }

    public String toJson() {
        return "{\"type\":\"" + type.name() + "\",\"message\":" + message + "}";
    }

    public static Message fromJson(String json) {
        String typeStr = getValue(json, "type");
        MessageType type = MessageType.valueOf(typeStr);
        String message = getValue(json, "message");
        return new Message(type, message);
    }

    private static String getValue(String json, String key) {
        int start = json.indexOf("\"" + key + "\": ") + key.length() + 4;
        int end = 0;
        if (key.equals("type")) {
            start += 1;
            end = json.indexOf("\"", start);
        } else if (key.equals("message")) {
            end = json.length() - 1;
        }
        return json.substring(start, end);
    }
}

public class QuestionBank {
    private static final int DEFAULT_PORT = 3002;
    private static final int SERVER_PORT = 30020;
    private static final int NUM_QUESTIONS = 5;
    private static String LANGUAGE;
    private static int PORT_USED;
    // private static String USER_QUESTIONS;

    public static void main(String[] args) {
        LANGUAGE = args.length > 0 ? args[0] : "java";
        PORT_USED = getAvailablePort(DEFAULT_PORT);
        startServer();
    }

    private static int getAvailablePort(int port) {
        while (true) {
            try (ServerSocket serverSocket = new ServerSocket(port)) {
                return port;
            } catch (IOException e) {
                port++;
            }
        }
    }

    private static void startServer() {
        // Establish initial connection to TM so the TM can store the details of the QB
        sendDataToTM(new Message(MessageType.QUESTION_BANK, new QuestionBankMessage(LANGUAGE, PORT_USED).toJson()));

        try (ServerSocket serverSocket = new ServerSocket(PORT_USED)) {
            while (true) {
                try (Socket clientSocket = serverSocket.accept()) {
                    InputStream inputStream = clientSocket.getInputStream();
                    BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream));
                    String line;
                    while ((line = reader.readLine()) != null) {
                        Message message = Message.fromJson(line);
                        if (message.type.equals(MessageType.LOGIN)) {
                            LoginMessage login_msg = LoginMessage.fromJson(message.message);
                            System.out.println("User: " + login_msg.user + " logged in");

                            sendDataToTM(new Message(MessageType.QUESTIONS,
                                    new QuestionsMessage(login_msg.user, getRandomQuestions(LANGUAGE)).toJson()));
                        }
                        if (message.type.equals(MessageType.MARK)) {
                            MarkMessage mark_msg = MarkMessage.fromJson(message.message);
                            sendDataToTM(new Message(MessageType.MARKED, mark_answer(mark_msg).toJson()));
                        }
                    }
                } catch (IOException e) {
                    System.err.println("Error accepting client connection");
                }
            }
        } catch (IOException e) {
            System.err.println("Failed to start server on port " + PORT_USED);
            System.exit(1);
        }
    }

    public static List<Question> getRandomQuestions(String filename) throws IOException {
        List<Question> questions = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(new FileReader(filename + ".txt"))) {
            List<String> lines = new ArrayList<>();
            String line;

            // Read all lines from file
            while ((line = reader.readLine()) != null) {
                lines.add(line);
            }

            // Shuffle lines randomly
            Random rand = new Random();
            for (int i = 0; i < NUM_QUESTIONS; i++) {
                int randomIndex = rand.nextInt(lines.size());
                String randomLine = lines.get(randomIndex);
                questions.add(Question.fromJson(randomLine));
                lines.remove(randomIndex); // Remove line to avoid duplicate selection
            }
        }
        return questions;
    }

    private static void sendDataToTM(Message message) {
        System.out.println("Sending Data");
        try (Socket socket = new Socket("localhost", SERVER_PORT)) {
            OutputStream outputStream = socket.getOutputStream();
            outputStream.write((message.toJson() + "\n").getBytes());
            outputStream.close();
        } catch (IOException e) {
            System.err.println("Failed to connect to server on port " + SERVER_PORT);
            System.exit(1);
        }
    }

    private static MarkedMessage mark_answer(MarkMessage mark_msg) throws IOException {
        try (BufferedReader reader = new BufferedReader(new FileReader(LANGUAGE + ".txt"))) {

            String line;
            // Read all lines from file
            while ((line = reader.readLine()) != null) {
                Question question = Question.fromJson(line);
                if (question.id.equals(mark_msg.id)) {
                    System.out.println("ID: " + mark_msg.id + ", Answer: " + mark_msg.answer + ", Correct Answer: "
                            + question.answer);
                    if (question.type.equals("code")) {
                        UUID temp_file_uuid = UUID.randomUUID();
                        boolean failed = false;

                        Path path = Paths.get(temp_file_uuid.toString());
                        try {
                            Files.createDirectories(path);
                            System.out.println("Directory created successfully.");
                        } catch (IOException e) {
                            System.out.println("An error occurred while creating the directory: " + e.getMessage());
                        }

                        if (LANGUAGE.equals("java")) {
                            Path java_file = path.resolve("Main.java");
                            try (BufferedWriter writer = new BufferedWriter(new FileWriter(java_file.toString()))) {
                                writer.write(
                                        mark_msg.answer.replaceAll("\\\\r", "\r").replaceAll("\\\\n", "\n")
                                                .replaceAll("\\\\t", "\t"));
                                System.out.println("String written to the file successfully.");
                            } catch (IOException e) {
                                System.out.println("An error occurred while writing to the file: " + e.getMessage());
                            }

                            System.out.println(java_file.toString());
                            // Compile java
                            try {
                                ProcessBuilder processBuilder = new ProcessBuilder("javac", "Main.java");
                                processBuilder.redirectErrorStream(true);
                                processBuilder.directory(new File(path.toString())); // Set the working directory
                                Process process = processBuilder.start();
                                int exitCode = process.waitFor();

                                if (exitCode == 0) {
                                    System.out.println("Compilation successful.");
                                } else {
                                    System.out.println("Compilation failed.");
                                    try {
                                        Files.deleteIfExists(java_file);
                                        Files.deleteIfExists(path);
                                        System.out.println("Directory deleted successfully.");
                                    } catch (IOException e) {
                                        System.out.println(
                                                "An error occurred while deleting the directory: " + e.getMessage());
                                    }
                                    return new MarkedMessage(mark_msg.id, mark_msg.user, mark_msg.answer, false,
                                            question.answer);
                                }

                                BufferedReader reader2 = new BufferedReader(
                                        new InputStreamReader(process.getInputStream()));
                                String line2;
                                while ((line2 = reader2.readLine()) != null) {
                                    System.out.println(line2);
                                }
                                reader2.close();
                            } catch (IOException | InterruptedException e) {
                                System.out
                                        .println("An error occurred while compiling the Java file: " + e.getMessage());
                            }

                            // Run java code
                            boolean passed = run_tests(question.tests, path, "java", "Main");
                            if (!passed) {
                                failed = true;
                            }

                            try {
                                Files.deleteIfExists(path.resolve("Main.class"));
                                Files.deleteIfExists(java_file);
                                Files.deleteIfExists(path);
                                System.out.println("Directory deleted successfully.");
                            } catch (IOException e) {
                                System.out.println("An error occurred while deleting the directory: " + e.getMessage());
                            }
                        } else if (LANGUAGE.equals("python")) {
                            Path python_file = path.resolve("main.py");
                            try (BufferedWriter writer = new BufferedWriter(new FileWriter(python_file.toString()))) {
                                writer.write(
                                        mark_msg.answer.replaceAll("\\\\r", "\r").replaceAll("\\\\n", "\n")
                                                .replaceAll("\\\\t", "\t"));
                                System.out.println("String written to the file successfully.");
                            } catch (IOException e) {
                                System.out.println("An error occurred while writing to the file: " + e.getMessage());
                            }

                            System.out.println(python_file.toString());

                            // Run python code
                            System.out.println(question.tests.size());
                            boolean passed = run_tests(question.tests, path, "python", "main.py");
                            if (!passed) {
                                failed = true;
                            }

                            try {
                                Files.deleteIfExists(python_file);
                                Files.deleteIfExists(path);
                                System.out.println("Directory deleted successfully.");
                            } catch (IOException e) {
                                System.out.println("An error occurred while deleting the directory: " + e.getMessage());
                            }
                        }
                        // Passed tests so return the 'correct' MarkedMessage
                        System.out.println("Tests passed.");
                        return new MarkedMessage(mark_msg.id, mark_msg.user, mark_msg.answer, !failed, question.answer);
                    } else if (question.id.equals(mark_msg.id)) {
                        return new MarkedMessage(mark_msg.id, mark_msg.user, mark_msg.answer,
                                mark_msg.answer.equals(question.answer), question.answer);
                    }
                }
            }
        }
        return new MarkedMessage(mark_msg.id, mark_msg.user, mark_msg.answer, false, "Could not find question");
    }

    private static boolean run_tests(List<Test> tests, Path path, String... run_args) {
        // Run code
        for (Test test : tests) {
            System.out.println("Starting test...");

            System.out.println("Parameters of test:");
            System.out.println("_______________");
            for (String param : test.parameters) {
                System.out.println(param);
            }
            System.out.println("_______________");
            System.out.println();

            try {
                ProcessBuilder processBuilder = new ProcessBuilder(run_args);
                processBuilder.redirectErrorStream(true);
                processBuilder.directory(new File(path.toString())); // Set the working directory
                List<String> args = processBuilder.command();
                args.addAll(test.parameters);
                Process process = processBuilder.start();

                // Set the timeout for the process
                long timeout = 2;
                TimeUnit unit = TimeUnit.SECONDS;
                boolean processCompleted;
                try {
                    processCompleted = process.waitFor(timeout, unit);
                } catch (InterruptedException e) {
                    processCompleted = false;
                }

                if (!processCompleted) {
                    // Process did not complete within the timeout
                    System.out.println("Run failed due to timeout.");
                    process.destroy(); // Terminate the process
                    return false;
                }

                if (process.exitValue() == 0) {
                    System.out.println("Run successful.");
                } else {
                    System.out.println("Run failed.");
                    return false;
                }

                StringBuilder output = new StringBuilder();
                BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                String line;
                while ((line = reader.readLine()) != null) {
                    System.out.println(line);
                    output.append(line).append("\n");
                }
                reader.close();

                System.out.println("Output of test:");
                System.out.println("_______________");
                System.out.println(output.toString());
                System.out.println("_______________");
                System.out.println();

                System.out.println("Expected output of test:");
                System.out.println("_______________");
                System.out.println(test.output);
                System.out.println("_______________");
                System.out.println();

                // Failed test
                if (!output.toString().equals(test.output)) {
                    System.out.println("Test failed.");
                    return false;
                }
            } catch (IOException e) {
                System.out.println("An error occurred running test program: " + e.getMessage());
                return false;
            }
        }
        return true;

    }
}