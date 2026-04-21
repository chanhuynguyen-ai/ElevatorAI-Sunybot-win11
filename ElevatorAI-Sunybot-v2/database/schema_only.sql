--
-- PostgreSQL database dump
--

\restrict xFH28P2LUiOnG763l9cK3PbhOZHaDlobfTUjj6JHkmpYM6TU4sBdzDGWcT3wSsD

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: camera_events; Type: TABLE; Schema: public; Owner: elevator_ai
--

CREATE TABLE public.camera_events (
    event_id bigint NOT NULL,
    event_ts timestamp with time zone DEFAULT now() NOT NULL,
    cam_id text NOT NULL,
    event_type text NOT NULL,
    track_id text,
    person_id integer,
    person_name text,
    bbox jsonb,
    posture text,
    people_count integer,
    confidence real,
    snapshot_path text,
    extra jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.camera_events OWNER TO elevator_ai;

--
-- Name: camera_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: elevator_ai
--

CREATE SEQUENCE public.camera_events_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.camera_events_event_id_seq OWNER TO elevator_ai;

--
-- Name: camera_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: elevator_ai
--

ALTER SEQUENCE public.camera_events_event_id_seq OWNED BY public.camera_events.event_id;


--
-- Name: camera_occupancy_samples; Type: TABLE; Schema: public; Owner: elevator_ai
--

CREATE TABLE public.camera_occupancy_samples (
    sample_id bigint NOT NULL,
    sample_ts timestamp with time zone DEFAULT now() NOT NULL,
    cam_id text NOT NULL,
    people_count integer NOT NULL,
    unknown_count integer DEFAULT 0 NOT NULL,
    lying_count integer DEFAULT 0 NOT NULL,
    fall_count integer DEFAULT 0 NOT NULL,
    extra jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.camera_occupancy_samples OWNER TO elevator_ai;

--
-- Name: camera_occupancy_samples_sample_id_seq; Type: SEQUENCE; Schema: public; Owner: elevator_ai
--

CREATE SEQUENCE public.camera_occupancy_samples_sample_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.camera_occupancy_samples_sample_id_seq OWNER TO elevator_ai;

--
-- Name: camera_occupancy_samples_sample_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: elevator_ai
--

ALTER SEQUENCE public.camera_occupancy_samples_sample_id_seq OWNED BY public.camera_occupancy_samples.sample_id;


--
-- Name: camera_events event_id; Type: DEFAULT; Schema: public; Owner: elevator_ai
--

ALTER TABLE ONLY public.camera_events ALTER COLUMN event_id SET DEFAULT nextval('public.camera_events_event_id_seq'::regclass);


--
-- Name: camera_occupancy_samples sample_id; Type: DEFAULT; Schema: public; Owner: elevator_ai
--

ALTER TABLE ONLY public.camera_occupancy_samples ALTER COLUMN sample_id SET DEFAULT nextval('public.camera_occupancy_samples_sample_id_seq'::regclass);


--
-- Name: camera_events camera_events_pkey; Type: CONSTRAINT; Schema: public; Owner: elevator_ai
--

ALTER TABLE ONLY public.camera_events
    ADD CONSTRAINT camera_events_pkey PRIMARY KEY (event_id);


--
-- Name: camera_occupancy_samples camera_occupancy_samples_pkey; Type: CONSTRAINT; Schema: public; Owner: elevator_ai
--

ALTER TABLE ONLY public.camera_occupancy_samples
    ADD CONSTRAINT camera_occupancy_samples_pkey PRIMARY KEY (sample_id);


--
-- Name: idx_camera_events_cam_ts; Type: INDEX; Schema: public; Owner: elevator_ai
--

CREATE INDEX idx_camera_events_cam_ts ON public.camera_events USING btree (cam_id, event_ts DESC);


--
-- Name: idx_camera_events_ts; Type: INDEX; Schema: public; Owner: elevator_ai
--

CREATE INDEX idx_camera_events_ts ON public.camera_events USING btree (event_ts DESC);


--
-- Name: idx_camera_events_type_ts; Type: INDEX; Schema: public; Owner: elevator_ai
--

CREATE INDEX idx_camera_events_type_ts ON public.camera_events USING btree (event_type, event_ts DESC);


--
-- Name: idx_occ_cam_ts; Type: INDEX; Schema: public; Owner: elevator_ai
--

CREATE INDEX idx_occ_cam_ts ON public.camera_occupancy_samples USING btree (cam_id, sample_ts DESC);


--
-- Name: idx_occ_ts; Type: INDEX; Schema: public; Owner: elevator_ai
--

CREATE INDEX idx_occ_ts ON public.camera_occupancy_samples USING btree (sample_ts DESC);


--
-- PostgreSQL database dump complete
--

\unrestrict xFH28P2LUiOnG763l9cK3PbhOZHaDlobfTUjj6JHkmpYM6TU4sBdzDGWcT3wSsD

