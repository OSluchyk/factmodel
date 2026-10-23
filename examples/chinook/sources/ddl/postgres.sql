-- Chinook schema, written by hand for FactModel from the public schema description
-- (eleven tables). Dialect: postgres. Schema only: rows are synthetic (seed/seed.py).

CREATE TABLE "Artist" (
  "ArtistId" INTEGER NOT NULL,
  "Name" VARCHAR(120),
  CONSTRAINT "PK_Artist" PRIMARY KEY ("ArtistId")
);

CREATE TABLE "Album" (
  "AlbumId" INTEGER NOT NULL,
  "Title" VARCHAR(160) NOT NULL,
  "ArtistId" INTEGER NOT NULL,
  CONSTRAINT "PK_Album" PRIMARY KEY ("AlbumId"),
  CONSTRAINT "FK_AlbumArtistId" FOREIGN KEY ("ArtistId") REFERENCES "Artist" ("ArtistId")
);

CREATE TABLE "Genre" (
  "GenreId" INTEGER NOT NULL,
  "Name" VARCHAR(120),
  CONSTRAINT "PK_Genre" PRIMARY KEY ("GenreId")
);

CREATE TABLE "MediaType" (
  "MediaTypeId" INTEGER NOT NULL,
  "Name" VARCHAR(120),
  CONSTRAINT "PK_MediaType" PRIMARY KEY ("MediaTypeId")
);

CREATE TABLE "Track" (
  "TrackId" INTEGER NOT NULL,
  "Name" VARCHAR(200) NOT NULL,
  "AlbumId" INTEGER,
  "MediaTypeId" INTEGER NOT NULL,
  "GenreId" INTEGER,
  "Composer" VARCHAR(220),
  "Milliseconds" INTEGER NOT NULL,
  "Bytes" INTEGER,
  "UnitPrice" NUMERIC(10,2) NOT NULL,
  CONSTRAINT "PK_Track" PRIMARY KEY ("TrackId"),
  CONSTRAINT "FK_TrackAlbumId" FOREIGN KEY ("AlbumId") REFERENCES "Album" ("AlbumId"),
  CONSTRAINT "FK_TrackGenreId" FOREIGN KEY ("GenreId") REFERENCES "Genre" ("GenreId"),
  CONSTRAINT "FK_TrackMediaTypeId" FOREIGN KEY ("MediaTypeId") REFERENCES "MediaType" ("MediaTypeId")
);

CREATE TABLE "Playlist" (
  "PlaylistId" INTEGER NOT NULL,
  "Name" VARCHAR(120),
  CONSTRAINT "PK_Playlist" PRIMARY KEY ("PlaylistId")
);

CREATE TABLE "PlaylistTrack" (
  "PlaylistId" INTEGER NOT NULL,
  "TrackId" INTEGER NOT NULL,
  CONSTRAINT "PK_PlaylistTrack" PRIMARY KEY ("PlaylistId", "TrackId"),
  CONSTRAINT "FK_PlaylistTrackPlaylistId" FOREIGN KEY ("PlaylistId") REFERENCES "Playlist" ("PlaylistId"),
  CONSTRAINT "FK_PlaylistTrackTrackId" FOREIGN KEY ("TrackId") REFERENCES "Track" ("TrackId")
);

CREATE TABLE "Employee" (
  "EmployeeId" INTEGER NOT NULL,
  "LastName" VARCHAR(20) NOT NULL,
  "FirstName" VARCHAR(20) NOT NULL,
  "Title" VARCHAR(30),
  "ReportsTo" INTEGER,
  "BirthDate" TIMESTAMP,
  "HireDate" TIMESTAMP,
  "Address" VARCHAR(70),
  "City" VARCHAR(40),
  "State" VARCHAR(40),
  "Country" VARCHAR(40),
  "PostalCode" VARCHAR(10),
  "Phone" VARCHAR(24),
  "Fax" VARCHAR(24),
  "Email" VARCHAR(60),
  CONSTRAINT "PK_Employee" PRIMARY KEY ("EmployeeId"),
  CONSTRAINT "FK_EmployeeReportsTo" FOREIGN KEY ("ReportsTo") REFERENCES "Employee" ("EmployeeId")
);

CREATE TABLE "Customer" (
  "CustomerId" INTEGER NOT NULL,
  "FirstName" VARCHAR(40) NOT NULL,
  "LastName" VARCHAR(20) NOT NULL,
  "Company" VARCHAR(80),
  "Address" VARCHAR(70),
  "City" VARCHAR(40),
  "State" VARCHAR(40),
  "Country" VARCHAR(40),
  "PostalCode" VARCHAR(10),
  "Phone" VARCHAR(24),
  "Fax" VARCHAR(24),
  "Email" VARCHAR(60) NOT NULL,
  "SupportRepId" INTEGER,
  CONSTRAINT "PK_Customer" PRIMARY KEY ("CustomerId"),
  CONSTRAINT "FK_CustomerSupportRepId" FOREIGN KEY ("SupportRepId") REFERENCES "Employee" ("EmployeeId")
);

CREATE TABLE "Invoice" (
  "InvoiceId" INTEGER NOT NULL,
  "CustomerId" INTEGER NOT NULL,
  "InvoiceDate" TIMESTAMP NOT NULL,
  "BillingAddress" VARCHAR(70),
  "BillingCity" VARCHAR(40),
  "BillingState" VARCHAR(40),
  "BillingCountry" VARCHAR(40),
  "BillingPostalCode" VARCHAR(10),
  "Total" NUMERIC(10,2) NOT NULL,
  CONSTRAINT "PK_Invoice" PRIMARY KEY ("InvoiceId"),
  CONSTRAINT "FK_InvoiceCustomerId" FOREIGN KEY ("CustomerId") REFERENCES "Customer" ("CustomerId")
);

CREATE TABLE "InvoiceLine" (
  "InvoiceLineId" INTEGER NOT NULL,
  "InvoiceId" INTEGER NOT NULL,
  "TrackId" INTEGER NOT NULL,
  "UnitPrice" NUMERIC(10,2) NOT NULL,
  "Quantity" INTEGER NOT NULL,
  CONSTRAINT "PK_InvoiceLine" PRIMARY KEY ("InvoiceLineId"),
  CONSTRAINT "FK_InvoiceLineInvoiceId" FOREIGN KEY ("InvoiceId") REFERENCES "Invoice" ("InvoiceId"),
  CONSTRAINT "FK_InvoiceLineTrackId" FOREIGN KEY ("TrackId") REFERENCES "Track" ("TrackId")
);
