import React from 'react'
import styles from './styles/Form.module.scss'
import { useForm, useFieldArray } from "react-hook-form";
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';


const Form = () => {
    const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;
    const [answer, setAnswer] = React.useState("");
    const [urls, setUrls] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const [mode, setMode] = React.useState("query");

    const { register, control, handleSubmit, reset, formState: { errors } } = useForm({
        defaultValues: {
            urls: [{ link: "" }],
            query: ""
        }
    });

    const { fields, append, remove } = useFieldArray({
        control,
        name: "urls"
    });

    const onSubmit = (data) => {
        console.log("Submitted Data:", data);
        setLoading(true);
        setAnswer("");
        setUrls([]);

        const urls = data.urls.map(u => u.link);
        const query = data.query || "Explain the content";

        const endpoint =
            mode === "query"
                ? "http://127.0.0.1:10000/process_url_query"
                : "http://127.0.0.1:10000/process_url_summary";

        const payload =
            mode === "query"
                ? { urls, query }
                : { urls };

        axios.post(endpoint, payload, {
            headers: { 'Content-Type': 'application/json' },
            withCredentials: false
        })
            .then(response => {
                console.log("Response from server:", response.data);
                setAnswer(response.data.answer);
                setUrls(response.data.sources || []);
                reset();
            })
            .catch(error => {
                console.error("Error submitting URLs:", error);
            })
            .finally(() => {
                setLoading(false);
            });
    };

    function cleanMarkdownTables(md) {
        return md
            .split('\n')
            .map(line => {
                if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
                    // Count how many columns in first line
                    const cols = line.split('|').filter(Boolean).length;
                    return line
                        .split('|')
                        .filter((seg, i) => i !== 0 && i !== cols)  // Remove leading/trailing empty
                        .map(seg => seg.trim())
                        .join(' | ');
                }
                return line;
            })
            .join('\n');
    }


    return (
        <div className={styles.container}>
            <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
                <h2>Add URLs</h2>

                {fields.map((field, index) => (
                    <div key={field.id} className={styles.urlGroup}>
                        <input
                            type="text"
                            {...register(`urls.${index}.link`, { required: true })}
                            placeholder="Enter URL"
                            className={styles.input}
                        />
                        <button type="button" onClick={() => remove(index)} className={styles.removeButton}>
                            Remove
                        </button>
                    </div>
                ))}

                <button
                    type="button"
                    onClick={() => append({ link: "" })}
                    className={styles.button}
                >
                    + Add URL
                </button>

                <h3>Select Mode</h3>
                <div className={styles.modeSelector}>
                    <label>
                        <input
                            type="radio"
                            value="query"
                            checked={mode === "query"}
                            onChange={() => setMode("query")}
                        />
                        <span>Query</span>
                    </label>
                    <label>
                        <input
                            type="radio"
                            value="summary"
                            checked={mode === "summary"}
                            onChange={() => setMode("summary")}
                        />
                        <span>Summary</span>
                    </label>
                </div>

                {mode === "query" && (
                    <>
                        <h3>Query</h3>
                        <textarea
                            {...register("query", { required: true })}
                            placeholder="Enter your question..."
                            className={styles.queryInput}
                            rows={4}
                        />
                        {errors.query && <span style={{ color: "red" }}>This field is required</span>}
                    </>
                )}

                {loading ? (
                    <div className={styles.loader}>⏳ Processing... Please wait</div>
                ) : (
                    <button type="submit" className={`${styles.button} ${styles.submitButton}`}>
                        Submit
                    </button>
                )}
            </form>

            <div className={styles.rightPanel}>
                {answer && (
                    <div className={styles.answerContainer}>
                        <h3>Answer</h3>
                        <div className={styles.answerMarkdown}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {cleanMarkdownTables(answer)}
                            </ReactMarkdown>
                        </div>
                    </div>
                )}

                {urls.length > 0 && (
                    <div className={styles.urlsContainer}>
                        <h3>Sources</h3>
                        <ul>
                            {urls.map((url, index) => (
                                <li key={index}>
                                    <a href={url} target="_blank" rel="noopener noreferrer">
                                        {url}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    )

}

export default Form;
